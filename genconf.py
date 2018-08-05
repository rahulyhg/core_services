import os
import sys
import getpass

modname = "vedavaapi"
apache_conf_template = "wsgi/wsgi_apache_template.conf"
confdir = os.path.join(modname, "conf_local")

user = getpass.getuser()
pwd = os.getcwd()

if not os.path.exists(confdir):
    os.makedirs(confdir)
with open(apache_conf_template) as f:
    content = f.read()
    content = content.replace('$USER', user).replace('$GROUP', user).replace('$SRCDIR', pwd).replace('$MOD', modname)
    targetfile = os.path.join(confdir, "wsgi_apache_" + modname + ".conf")
    try:
        with open(targetfile, "w") as newf:
            newf.write(content)
    except Exception as e:
        print "Could not write " + targetfile + ": ", e
        sys.exit(1)
