import requests
import json
import lxml.html as lhtml
import contextlib
import base64, urllib2, urllib
import dateutil.parser
import nltk
from nltk.tokenize import RegexpTokenizer
import argparse
import re

MAX_NGRAM_LENGTH = 10

class WordToken:
    def __init__(self, text, start, end):
        self.text = text[start:end]
        self.start = start
        self.end = end

class NGramToken:
    def __init__(self, word_tokens):
        self.text = ' '.join([token.text for token in word_tokens])
        self.start = word_tokens[0].start
        self.end = word_tokens[-1].end

class TaggedToken:
    def __init__(self, tag, token):
        self.tag = tag
        self.token = token

word_tokenizer = RegexpTokenizer('(\w|-)+|\$[\d\.]+|[\"\.,\?\!\'\(\)]|\S+')

def word_token_gen(text):
    """
    Parse the text into a series of WorkTokens.
    I don't use the default nltk work tokenizer here because it doesn't include offsets.
    Instead I am using a RegexpTokenizer which does not do a good of job
    on things like contractions.
    The sentence tokenizer is probably not necessairy at the moment,
    but if the work tokenizer is replaced with something more complex it might
    be needed.
    """
    sent_tokenizer = nltk.load('tokenizers/punkt/english.pickle')
    for sent_offsets in sent_tokenizer.span_tokenize(text):
        for word_offsets in word_tokenizer.span_tokenize(text[sent_offsets[0]:sent_offsets[1]]):
            yield WordToken(
                text,
                sent_offsets[0] + word_offsets[0],
                sent_offsets[0] + word_offsets[1]
            )

def tagged_token_gen(tags, word_tokens):
    """
    Find consecutive word tokens with text that matches a
    tag and combine them into a TaggedToken
    """
    token_accum = []
    for token in word_tokens:
        token_accum.append(token)
        for tag in tags:
            # Some tags only appear in the text in a pluralized form,
            # some are capitalized, some have leading whitespace, some have
            # things like / in them. The regex and tokenizing tries to sort that
            # all out so they still match the intended text.
            tokenized_tag_text = ' '.join(word_tokenizer.tokenize(tag.get('tag')))
            tag_regex = re.compile('^' + tokenized_tag_text + 's?$', re.I)
            ngram_token = NGramToken(token_accum[-1:])
            for gram_length in range(len(token_accum[-MAX_NGRAM_LENGTH:])):
                ngram_token = NGramToken(token_accum[-1 - gram_length:])
                if tag_regex.match(ngram_token.text):
                    yield TaggedToken(tag, ngram_token)

def generate_annotations_from_tags(
        resource,
        resource_tags,
        uri
    ):
    """
    Find all the occurances of the given tags in the resource text and 
    create annotations in the annotation database.
    """
    ### Upload annotations to the portfolio manager
    word_tokens = word_token_gen(resource.get('content'))    
    for tagged_token in tagged_token_gen(resource_tags, word_tokens):
        text = tagged_token.tag.get('tag')
        if tagged_token.tag.get('category'):
            text += ',\ncategory: ' + tagged_token.tag.get('category')
        if tagged_token.tag.get('addedBy') == 'annotabot':
            text += '\n-Annotabot' 
        yield {
            'text' : text,
            'quote' : tagged_token.tag.get('tag'),
            'ranges' : [{
                'start' : "",
                'end' : "",
                'startOffset' : tagged_token.token.start,
                'endOffset' : tagged_token.token.end
            }],
            'uri' : uri,
            'addedBy' : tagged_token.tag.get('addedBy'),
            'client' : 'annotabot-0.0.0'
        }
        
def upload_annotation(annotation, server_url, auth):
    req = urllib2.Request(server_url + "annotator/annotations",
        json.dumps(annotation),
        {'Content-Type': 'application/json'})
    req.add_header('Authorization',
        'Basic ' + base64.urlsafe_b64encode(auth[0]+':'+auth[1])
    )
    return urllib2.urlopen(req)

def fetch_tags(
    tag_csv_url = "https://ckan-datastore.s3.amazonaws.com/2013-12-05T16:33:55.912Z/tagging-brainstorm-sheet1.csv"
    ):
    tags = []
    with contextlib.closing(urllib2.urlopen(tag_csv_url)) as raw_csv:
        for line in raw_csv.read().split('\n'):
            if line:
                category, tag = line.split(',')
                if tag and not tag in tags:
                    tags.append({
                        'tag' : tag,
                        'addedBy' : 'annotabot',
                        'category' : category
                    })
    return tags
    
def process_resource(resource):
    #I html parse the resource to handle some of the issues with html entities and tags.
    #Content is nested in a body tag to preserve the leading spaces
    doc = lhtml.fromstring('<body>' + resource.get('content') + '</body>')
    #lxml has a few ways to generate strings. I'm using this one
    #because it doesn't replace apothophies and arrows with unicode points.
    text = lhtml.tostring(doc, method='text', encoding='unicode')
    #This replaces the non-breaking space code points,
    #there are probably others I'm missing.
    text = text.replace(u"\xa0", u" ")
    resource['content'] = text

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-username')
    parser.add_argument('-password')
    parser.add_argument('-resource_file')
    parser.add_argument('-server', help='annotator server', default='localhost/')
    args = parser.parse_args()
    auth = (args.username, args.password)
    if args.resource_file:
        print "Loading resources from " + args.resource_file
        with open(args.resource_file) as f:
            resources = json.load(f)
    else:
        print "Fetching resources from the portfolio manager..."
        r = requests.request("GET", args.server + "resources/", auth=auth)
        resources_text = r.text
        print "Resources downloaded from server"
        resources = json.loads(resources_text)
    print "Processing resources..."
    for resource in resources:
        process_resource(resource)
    print "Fetching tags..."
    tags = fetch_tags()
    print tags[0:10]
    for resource in resources:
        uri = args.server + 'annotatableResources/' + resource.get('_id')
        print "Annotating: " + uri
        resource_tags = [t for t in tags]
        # Filter out tags attached to the resource, there is another script
        # for annotating them.
        for key, value in resource.get('tags', {}).items():
            resource_tags = [t for t in resource_tags if t.get('tag') != key]
        for annotation in generate_annotations_from_tags(resource, resource_tags, uri):
            request = upload_annotation(annotation, args.server, auth)
            print json.loads(request.read()).get('quote')
