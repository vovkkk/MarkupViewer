import yaml, io, os
from pprint import pprint

with io.open('D:\\dev\\GitHub\\MarkdownViewer\\settings.yaml', 'r', encoding='utf8') as f:
    settings = yaml.safe_load(f)

user_source = os.path.join(os.getenv('APPDATA'), 'MarkupViewer/settings.yaml')
with io.open(user_source, 'r', encoding='utf8') as f:
    settings.update(yaml.safe_load(f))
    # user_settings = yaml.safe_load(f)


pprint(settings)