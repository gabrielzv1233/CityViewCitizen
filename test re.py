import re
from markupsafe import escape
contents = """<c="red">cheese</c>"""
contents = escape(contents)
contents = re.sub(r'&lt;c=&#34;([^"]+)&#34;&gt;([^<]+)&lt;/c&gt;', r'<span style="color:\1">\2</span>', contents)
print(contents)