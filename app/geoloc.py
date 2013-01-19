import urllib
import re

def get_geolocation_from_ip():
	response = urllib.urlopen('http://api.hostip.info/get_html.php?ip=71.198.21.183&position=true').read()
	print "---------------- Geolocation report based on your IP address -------------"
	print(response)
	strlist = response.replace('\n', ' ').split(' ')
	latstr = strlist [strlist.index('Latitude:') + 1]
	lonstr = strlist [strlist.index('Longitude:') + 1]
	ipstr =  strlist [strlist.index('IP:') + 1]
	lat = float(latstr)
	lon = float(lonstr)
	print "-------------------------------------------------------------------------"
	url = 	"http://gisdata.usgs.gov/" \
		+ "xmlwebservices2/elevation_service.asmx/" \
		+ "getElevation?X_Value=" + lonstr \
		+ "&Y_Value=" + latstr \
		+ "&Elevation_Units=METERS&Source_Layer=-1&Elevation_Only=true"
	response = urllib.urlopen(url).read()
	alt = re.search('(<double>)(.*?)(</double>)', response).group(2)
	alt = float(alt)
	print response
	print "-------------------------------------------------------------------------"
	print "using location %f, %f, altitude %f meters based on IP address %s" % (lat, lon, alt, ipstr)
	print "-------------------------------------------------------------------------"

if __name__ == '__main__':
	get_geolocation_from_ip()
