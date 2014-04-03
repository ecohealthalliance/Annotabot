import requests
import json

def dict_to_url_params(d):
    params = ''
    prev = None
    for key, value in d.items():
        if prev:
            params += '&'
        else:
            params += '?'
        params += key + "=" + value
        prev = key
    return params

def remove_old_annotations(
        SERVER_URL = "http://54.83.200.115/",
        AUTH = None,
        criteria = None
    ):
    if criteria is None:
        criteria = {
            'client' : 'annotabot-0.0.0'
        }
    if AUTH is None: AUTH=(raw_input("username: "), raw_input("password: "))
    r = requests.request("GET", SERVER_URL + "annotator/search" + dict_to_url_params(criteria), auth=AUTH)
    annotations = json.loads(r.text)
    
    for annotation in annotations.get('rows'):
        print "Removing: http://54.83.200.115/annotator/annotations/" + annotation.get("id")
        r = requests.request("DELETE", "http://54.83.200.115/annotator/annotations/" + annotation.get("id"), auth=AUTH)
        print r
    print 'done'

if __name__ == "__main__":
    remove_old_annotations()