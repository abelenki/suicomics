#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging, re, os

try:
    from includes import *  #assign global variables in this module
except:
    logging.error('failed to load includes')
    global_vars = {}

gTempVarPtn = re.compile(ur'{{\s*([\w\|:"/.?_$()]+)\s*}}',re.UNICODE)
gMatchPtn = re.compile(r'([|:?])')

realpath = os.path.dirname(__file__)

class Templite():
    """ Simplistic template processing as an alternative to django template engine.
    Syntax:
    {{ var }} - replace var with its value, or do nothing if not found
    Loops and conditions are not supported.
    Supported: {{ varname }}, {{ varname|default:"" }}, {{ varname|date[time] }}, {{ include|subdir/file.html }}, {{ varname?true_var:false_var }}
    Some global values can be saved in global_vars in file includes.py.
    Other variables can be saved in a dict and pass as the vars argument to the constructor. eg. t = Templite({'var1':'value1'},out)
    """
    def __init__(self, vars=None, out=None):
        self.vars = vars or {}
        self.out = out
        
    def render(self, text, vars=None, out=None):
        """ Render the text by substituting the variables with values from the dict.
        @param text: HTML text to parse
        @param vars: dict containing the variables and values to put in the text for output
        @param out: output stream
        @return: True if successfule
        """
        if vars: self.vars = vars
        if out: self.out = out
        if self.out is None:
            logging.error('templite.render_text() output stream is None')
            raise Exception('No output')
        if text is None or text == '':
            logging.warning('templite.render_text() text parameter is empty')
            return False
        if text.find('{{') >= 0:
            #gTempVarPtn = re.compile(ur'{{\s*([\w\|:"/.]+)\s*}}',re.UNICODE)
            rs = gTempVarPtn.sub(self.get_value, text)
            self.out.write(rs)
        else:
            self.out.write(text)
        return True
        
    def get_values(self,s):
        """ Find and return value of key s in either self.vars or global_vars dictionary. 
            It returns None if not found. For global_vars, the result will be parsed for {{ v }} again. Be careful not to dead loop.
        """
        if s in self.vars:
            return self.vars[s]
        if s in global_vars:
            vs = global_vars[s]
            if vs.find('{{') >= 0:
                #logging.info('---------- parsing %s'%vs)
                return gTempVarPtn.sub(self.get_value, vs)
            return vs
        #logging.warning('!!!!!!! var "%s" not found in self.vars or global_vars'%s)
        return None
        
    def get_value(self,match):
        """ Return the value from self.vars, or error if not found. 
        Supported: {{ varname }}, {{ varname|default:"" }}, {{ varname|date[time] }}, {{ include|subdir/file.html }}, {{ varname?true_var:false_var }}
        """
        ps = gMatchPtn.split(match.group(1))
        n = len(ps)
        if n < 1:
            logging.error('Syntax error: nothing in {{}}')
            return '{{}}'
        var = ps[0]
        val = self.get_values(var)
        if val is None:
            if var == 'include':                #['include', '|', 'web/file.inc']
                return self.read_file(ps[2])
            elif n > 4 and ps[2] == 'default':  #['var1', '|', 'default', ':', '".."']
                return ps[4].replace('"','')
            elif len(ps)>1 and ps[1] == '?':
                if n > 4:
                    val = self.get_values(ps[4].strip())
                else:
                    val = ''
                n = 1
            else:
                rs = '{{ "%s" }} not found'%var
                logging.error(rs)
                return rs
        if n > 2:
            op = ps[1]
            if op == '?' and n > 2:          #['var', '?', 'true_s', ':', 'false_s'] the value of var must be bool type, :false_s is optional
                if not isinstance(val, bool):
                    logging.error('var is not bool in %s'%match.group(1))
                    return match.group(1)
                if val:
                    val = self.get_values(ps[2].strip())
                    #logging.info('!!!!!!! getting value %s=%s'%(ps[2],val))
                elif n > 4:
                    val = self.get_values(ps[4].strip())
                else:
                    val = ''
                if val is None:
                    return match.group(1)
            elif op == '|':                 #['var', '|', 'date[time]']
                r = ps[2]
                if r == 'datetime':
                    val = datetime.strftime(val,'%Y-%m-%d %H:%M:%S')
                elif r == 'date':
                    val = datetime.strftime(val,'%Y-%m-%d')
            else:
                logging.error('unknown op in %s'%match.group(1))
                return match.group(1)
        if isinstance(val,basestring):
            return val
        return jsonize(val)
       
    def read_file(self,filename):
        logging.info('read_file(%s)'%filename)
        if filename.find('$(')>=0:
             filename = re.sub(r'\$\((\w+)\)',lambda m: self.get_values(m.group(1)),filename)
             logging.info('\treplaced: %s'%filename)
        if filename.startswith('/'):
            sp = '%s%s'
        else:
            sp = '%s/%s'
        fi = open(sp % (realpath,filename))
        txt = fi.read()
        fi.close()
        return txt
        
def render_text(text, vars, out):
    """ Simple interface for Templite.render.
    @param text: HTML content text
    @param vars: {'var':value,...} where value is normally a string, but can be an object.
    @param out: output stream to send rendered text
    """
    #for k,v in vars.items():
    #    logging.info('k,v=%s,%s'%(k,v))
    t = Templite(vars, out)
    return t.render(text)

def render_file(file, vars, out):
    """ Read file content and calls render_text. """
    fi = open(file)
    txt = fi.read()
    fi.close()
    return render_text(txt, vars, out)
    
class Jsonizer():
    """ JSON rendering class to make a JSON-format string out of a Python object.
    Supported object types include dict, list and embedded recursively.
    Output is UTF-8 encoded.
    Special: if a string value starts with {, it is treated as dict string, no quote is added.
    """
    def __init__(self):
        self.buf = []

    def jsonize(self, data):
        self.buf = []
        self.make_data(data)
        return ''.join(self.buf)

    def make_data(self, data):
        if isinstance(data, dict):
            self.make_dict(data)
        elif isinstance(data, list):
            self.make_list(data)
        elif isinstance(data, basestring):
            if data.find('"') >= 0: data = data.replace('"',"'")
            if data.find('\r\n') >= 0: data = data.replace('\r\n','<br/>')
            if data.find('\n') >= 0: data = data.replace('\n','<br/>')
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            if data.startswith('{') or data.startswith('['):
                self.buf.append('%s' % data)
            else:
                self.buf.append('"%s"' % data)
        else:
            self.buf.append('%s' % data)    #numbers

    def make_dict(self, data):
        self.buf.append('{')
        count = 0
        for d in data.items():
            if count == 0:
                count += 1
            else:
                self.buf.append(',')
            self.buf.append('"%s":' % d[0]) #key
            self.make_data(d[1])    #value
        self.buf.append('}')

    def make_list(self, data):
        self.buf.append('[')
        count = 0
        for d in data:
            if count == 0:
                count += 1
            else:
                self.buf.append(',')
            self.make_data(d)
        self.buf.append(']')

def jsonize(data):
    """ Wrap Jsonizer.jsonize into a simple method.
    @param data: dict or array object to render into a JSON string.
    @return JSON-format string.
    """
    json = Jsonizer()
    return json.jsonize(data)
    