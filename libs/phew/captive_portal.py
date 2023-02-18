from libs.phew import server, dns
from libs.phew.template import render_template  # type: ignore comment;
import conf as c

## ---- CAPTIVE PORTAL -----
# https://picockpit.com/raspberry-pi/raspberry-pi-pico-w-captive-portal-hotspot-access-point-pop-up/

# microsoft windows
@server.route("/ncsi.txt")
@server.route("/connecttest.txt")
def hotspot(request):
    return "", 200

# android
@server.route("/redirect")
@server.route("/generate_204")
def hotspot(request):
    return server.redirect("http://upycms.wifi/", 302)

# apple
@server.route("/hotspot-detect.html", methods=["GET"])
def hotspot(request):
    # return render_template("index.html")
    return render_template("{}redirect.html".format(c.adm), location="/")

# Catch all requests and reroute them
# dns.run_catchall(ip)
## ---- END CAPTIVE PORTAL -----