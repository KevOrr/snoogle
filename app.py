import urllib, time
from html.parser import HTMLParser
from requests.exceptions import HTTPError

import praw, flask
from bs4 import BeautifulSoup as BS

KEEP_SAFE = False # KEEP_SAFE ensures that all HTML in comments gets escaped
LIMIT = 300 # Limit the number of comments fetched in `search`.

app = flask.Flask(__name__)
r = praw.Reddit('Comment Searcher for AyChihuahua v0.0 by elaifiknow')

@app.route('/')
def main():
    1/0
    with open('main.html') as f:
        return f.read()

@app.route('/search')
def search():
    last = time.time()
    try:
        # Get redditor
        user = r.get_redditor(flask.request.args['username'])
    except HTTPError:
        # Redditor likely doesn't exist
        user = {'name': flask.request.args['username'],
                '_url': 'http://www.reddit.com/u/' \
                        + flask.request.args['username']
               }
        last = time.time()
        soup = BS(flask.render_template('search.html', user=user))
        times = render_times(time.time() - last)
    else:
        # Get comments
        comments = user.get_comments(limit=LIMIT)
        time_fetching, last = time.time() - last, time.time()

        # Start search
        keywords = flask.request.args['keywords'].split()
        count, results = do_search(comments, keywords)
        time_searching, last = time.time() - last, time.time()
        
        # Sort results
        results.sort(key=lambda item: item[0], reverse=True)
        
        # Start rendering
        soup = BS(flask.render_template('search.html', results=results))
        time_rendering = time.time() - last
        times = render_times(time_fetching, time_searching, time_rendering, count=count)

    # Add times, prettify, and serve
    soup.body.append(BS(times))
    response = flask.make_response(soup.prettify())
    response.headers['content'] = 'text/html; charset=utf-8'
    return response

def do_search(comments, keywords):
    parser = HTMLParser()
    results = []
    parity = 1
    count = 0
    for comment in comments:
        count += 1
        parity = not parity
        relevancy = 0
        for keyword in keywords:
            relevancy += comment.body.lower().count(keyword.lower())
        if relevancy:
            results.append((relevancy, comment,
                            parser.unescape(comment.body_html),
                            get_parent(comment), ['even', 'odd'][parity]))
    return count, results

def get_parent(comment):
    if isinstance(comment, praw.objects.Comment):
        if comment.is_root:
            # Parent is the post, not another comment
            return comment.submission
        else:
            # Parent is another comment
            return r.get_info(thing_id=comment.parent_id)
    elif isinstance(comment, praw.objects.Submission):
        e = TypeError('Submissions don\'t have parents!')
        raise e
    else:
        _name = comment.__class__.__name__
        if comment.__class__.__name__ not in __builtins__:
            _name = comment.__class__.__module__ + _name
        e = TypeError(('comment must be of type praw.objects.Comment, not %s.' \
                      % _name) \
                      +'If you are using your own class, please inherit from praw.objects.Comment')
        raise e

def render_times(*times, count=None):
    if len(times) == 3:
        # Redditor exists, show all times
        if count is None:
            e = TypeError('Must specify comment count')
            raise e
        text = ('<div class="search-times">\n'
               +'<pre>Spent {: >7.3f} seconds fetching {count} (limit {limit}) comments</pre>\n'
               +'<pre>Spent {: >7.3f} seconds searching results</pre>\n'
               +'<pre>Spent {: >7.3f} seconds rendering template</pre>\n'
               +'<hr class="search-times-hr" />'
               +'<pre>Spent {total: >7.3f} seconds total</pre>\n'
               +'</div>')
        return text.format(*times, count=count, limit=LIMIT, total=sum(times))
    elif len(times) == 1:
        # Redditor does not exist, only show rendering time
        text = ('<div class="search-times">\n'
               +'<pre>Spent {: >7.3f} seconds rendering template</pre>\n'
               +'</div>')
        return text.format(*times)
    else:
        # I'm not really sure how you can get here, but it's here just in case
        return ''

if __name__ == '__main__':
    app.run(debug=True)
