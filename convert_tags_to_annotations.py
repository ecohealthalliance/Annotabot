from create_annotations_from_tags import *

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
    for resource in resources:
        print "Extracting tags..."
        tags = []
        for key, value in resource.get('tags', {}).items():
            if value.get('removed', False):
                continue
            tags.append({
                'tag' : key,
                'addedBy' : value.get('addedBy'),
                'dateAdded' : str(dateutil.parser.parse(value.get('dateAdded'))),
                'resourceId' : resource.get('_id')
            })
        uri = args.server + 'annotatableResources/' + resource.get('_id')
        print "Annotating: " + uri
        annotations = []
        for annotation in generate_annotations_from_tags(resource, tags, uri):
            annotations.append(annotation)
            request = upload_annotation(annotation, args.server, auth)
            print json.loads(request.read()).get('quote')
        if len(annotations)  < len(tags):
            tag_texts = [t.get('tag') for t in tags]
            if "severe respiratory infection" in tag_texts:
                print """
                There are more tags than annotations, but it's probably because
                the tag "severe respiratory infection" is not used in the article's text.
                """
                continue
            print tag_texts
            raise Exception("Something is wrong, there are more tags than annotations.")

