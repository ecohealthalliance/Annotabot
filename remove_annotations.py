import requests
import json
import urllib, urllib2
import argparse

def remove_old_annotations(
        annotator_api_url,
        auth,
        criteria = None
    ):
    if criteria is None:
        criteria = {
            'client' : 'annotabot-0.0.0'
        }
    r = requests.request("GET",
            annotator_api_url + "search?" + urllib.urlencode(criteria),
            auth=auth
        )
    annotations = json.loads(r.text)
    
    for annotation in annotations.get('rows'):
        print "Removing: " + annotator_api_url + "annotations/" + annotation.get("id")
        r = requests.request("DELETE",
            annotator_api_url + "annotations/" + annotation.get("id"),
            auth=auth
        )
        print r
    print 'done'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-username')
    parser.add_argument('-password')
    parser.add_argument('-server', help='annotator server', default='localhost/')
    args = parser.parse_args()
    remove_old_annotations(
        args.server + 'annotator/',
        auth=(args.username, args.password)
    )
