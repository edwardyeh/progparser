s/mod_pat_list = \[\]/mod_pat_list = \{\}/g
s/mod_pat_list\.append((\(..*\), \(..*\)))/mod_pat_list[\1] = \2/g
