#!/usr/bin/env python3

LIMIT = 300 # Limit the number of comments fetched in `search`.

import time, urllib, sys
from html.parser import HTMLParser
import atexit, cProfile

from requests.exceptions import HTTPError
import praw, flask
from flask import Flask, make_response, render_template, url_for
from bs4 import BeautifulSoup as BS

app = flask.Flask(__name__)
r = praw.Reddit('Snoogle Comment Searcher v0.1 by elaifiknow')

#####################
### Begin Routing ###
#####################

@app.route('/')
def main():
    response = app.send_static_file('index.html')
    response.headers['content'] = 'text/html; charset=utf-8'
    return response

##################
# Comment Search #
##################

@app.route('/search')
def search():
    print('Received Search request')
    last = time.time()
    if 'username' not in flask.request.args or 'keywords' not in flask.request.args:
        return flask.redirect('/')
    else:
        username = flask.request.args['username']
        keywords = flask.request.args['keywords'].split()
    try:
        # Get redditor
        user = r.get_redditor(username)
    except HTTPError:
        # Redditor likely doesn't exist
        user = {'name': username,
                '_url': 'http://www.reddit.com/u/' + username
               }
        last = time.time()
        soup = BS(render_template('search.html', user=user))
        times = render_times(time.time() - last)
    else:
        # Get comments
        comments = user.get_comments(limit=LIMIT)
        time_fetching = time.time() - last
        last = time.time()

        # Do the search
        count, results = do_search(comments, keywords)
        time_searching = time.time() - last
        
        # Sort results
        results.sort(key=lambda item: item[0], reverse=True)
        
        # Start rendering
        last = time.time()
        # html = Profiler(render_template, 'search.html', results=results).profile_stdout()
        html = render_template('search.html', results=results)
        time_rendering = time.time() - last

        # Add on render times
        soup = BS(html)
        times = render_times(time_fetching, time_searching, time_rendering, count=count)

    # Add times, prettify, and serve
    soup.body.append(BS(times))
    response = make_response(soup.prettify())
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
            results.append((relevancy,
                            comment,
                            parser.unescape(comment.body_html),
                            # get_parent(comment),
                            ['even', 'odd'][parity]))
    return count, results

"""def get_parent(comment):
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
"""

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
        # I'm not really sure how you got here, but it's here just in case
        return ''

#################################
### Debugging/Profiling Stuff ###
#################################

class Profiler():
    def __init__(self, func, *args, **kwargs):
        self.p = cProfile.Profile()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def profile_file(self, filename):
        result = p.runcall(func, *self.args, **self.kwargs)
        p.dump_stats(filename)
        return result

    def profile_stdout(self):
        result = p.runcall(func, *args, **kwargs)
        p.print_stats(sort=-1)
        return result

def profile_wrapper(filename=None):
    def decorator(func):
        def decorated(*args, **kwargs):
            if filename:
                return Profiler(func, *args, **kwargs).profile_file(filename)
            else:
                return Profiler(func, *args, **kwargs).profile_stdout()
        return decorated
    return decorator

############
### MAIN ###
############

if __name__ == '__main__':
    atexit.register(print, 'Program exited')
    if 'debug' in sys.argv:
        app.run('127.0.0.1', debug=True)
    else:
        app.run(debug=True)
