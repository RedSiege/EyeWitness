import re


class Regex:
	http_regex_string = "^http[s]?://"
	vnc_regex_string = "^vnc[s]?://"
	rdp_regex_string = "^rdp[s]?://"
	http_regex = re.compile(http_regex_string, re.IGNORECASE)
	vnc_regex = re.compile(vnc_regex_string, re.IGNORECASE)
	rdp_regex = re.compile(rdp_regex_string, re.IGNORECASE)


	@staticmethod
	def isHTTP(string):
		if not re.match(Regex.http_regex, string):
			return False
		return True


	@staticmethod
	def isVNC(string):
		if not re.match(Regex.vnc_regex, string):
			return False
		return True


	@staticmethod
	def isRDP(string):
		if not re.match(Regex.rdp_regex, string):
			return False
		return True
