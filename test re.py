import re

text = "- |bullet point"
contents = re.sub(r'^- \|(.*)$', r'<li>\1</li>', contents)
print(result)