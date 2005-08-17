#!/usr/bin/python
# $Id$

RCFILE = '.noterc'





# ================== #
#  DON"T EDIT BELOW  #
# ================== #

__version__ = '0.3'
__author__  = 'Marcin ``MySZ`` Sztolcman'
__date__    = '2005.08.16'
__license__ = 'GPL v.2'
__home__    = 'http://urzenia.net/proj/misc/note'

# ==== #
# TODO #
# ==== #
"""
- first read .noterc in '.', next in '~'
"""
# ==== #
# DONE #
# ==== #
"""
- do not add empty notes
- interactive mode
- rnote must to know, how to use parameters when we call:
    # rnote 2 4 7
  in this case it must show notes at id's 2, 4 and 7
- inote must recognized switches:
    -v (version)
    -h (help)
- rnote must recognized switches:
    -v (version)
    -h (help)
- add history file via readline module
"""


#modules
import ConfigParser
import os, sys, imp
import getopt
import time
from cmd import Cmd
try:
  import readline
except ImportError:
  pass






def VERSION(prog = None):
  if not prog: prog = 'note'
  print """
  %(prog)s %(ver)s :: %(date)s :: %(author)s :: %(license)s
  homepage: %(home)s""" % {
    'prog': prog,
    'ver': __version__,
    'date': __date__,
    'author': __author__,
    'license': __license__,
    'home': __home__
  }


def USAGE():
  progname = os.path.basename(sys.argv[0])
  VERSION()
  if progname in ('note', 'note.py'):
    print """
Note is program, which stores sam notes (like 'yellow cards') in database
(BerkeleyDB type), and prints them, delete, list etc. I cal 'rnote.py'
from my ~/.zshrc, and when I log in to my server, it prints me what I have
to do :)

Usage:
  note [-a|--add] [-d|--del id_note] [-l|--list] [-i|--iactive]
       [-h|--help] [-v|--version] [note]

-a | --add          - add note to database
-d | --del id_note  - remove note from database
-l | --list         - lists all notes
-i | --iactive      - enter interactive mode
-h | --help         - show this help
-v | --version      - print version and exit

Default options is --add, so You can call note:
  note it is my note

and 'it is my note' will be stored in database.
"""
  elif progname in ('rnote', 'rnote.py'):
    print """
By default, rnote.py prints all the notes. If you specify id after program
name (for example: rnote.py 2 4), this show only selected notes.

Usage:
  rnote [-v|--version] [-h|--help] [id_note id_note ...]

-v | --version      - print version and exit
-h | --help         - show this help

Look for note.py --help for more info.
"""
  elif progname in ('inote', 'inote.py'):
    print """
Start note.py in interactive mode (like 'note.py --iactive').

Usage:
  inote [-v|--version] [-h|--help]

-v | --version      - print version and exit
-h | --help         - show this help

Look for note.py --help for more info.
"""



class Container:
  def __init__(self):
    pass
  def getval(self, *opt):
    if opt:
      return [ getattr(self, o) for o in opt if hasattr(self, o) ]
    else:
      ret = {}
      for attr in dir(self):
        meth = getattr(self, attr)
        if not attr.startswith('_') and not callable(meth):
            ret[attr] = meth
      return ret
  def __getitem__(self, key):
    if hasattr(self, key):
      return getattr(self, key)
    else:
      raise KeyError
  def __setitem__(self, key, value):
    setattr(self, key, value)
  def __delitem__(self, key):
    del self.key
  def __len__(self):
    return len(self.getval())



class Cmdline(Cmd):
  def __init__(self, prompt = None):
    Cmd.__init__(self)
    if prompt is not None:
      self.prompt = prompt
    else:
      self.prompt = 'note> '
    self.intro = """note interactive mode
    version:  %(version)s
    author:   %(author)s
    date:     %(date)s
""" % {'version': __version__, 'author': __author__, 'date': __date__}
  def do_list(self, args):
    '''lists all entries'''
    self.list_notes()
      
  def do_show(self, args):
    '''show selected entry'''
    args = args.split()
    self.show_note(args)
  def do_add(self, args):
    '''add new note'''
    self.add_note(args)
  def do_del(self, args):
    '''del selected note'''
    args = args.split()
    self.del_note(args)
  def do_clear(self, args):
    '''clear all notes'''
    self.clear_notes()

  def do_quit(self, args):
    '''quits interactive mode'''
    raise SystemExit
  def emptyline(self):
    '''override Cmd.emptyline() for non action on empty command'''
    pass
  def start(self):
    try:
      self.cmdloop()
    except KeyboardInterrupt:
      self.do_quit(None)

  #shortcuts
  do_q = do_quit
  do_a = do_add
  do_l = do_list
  do_s = do_show
  do_EOF = do_quit



class Note(Cmdline):
  def __init__(self):
    #read config
    cfg = self._parse_config()

    Cmdline.__init__(self, cfg['prompt'])

    #import approbiate module
    fp, path, desc = imp.find_module(cfg['dbtype'])
    try:
      db_mod = imp.load_module(cfg['dbtype'], fp, path, desc)
    finally:
      if fp: fp.close()
    del fp, path, desc



    #open and save db handler
    path = os.path.join(os.path.expanduser('~'), self.config.dbfname)
    try:
      self.db = db_mod.open(path, 'c')
    except (OSError, IOError):
      print >>sys.stderr, 'Cannot open/create db file (%s).' % cfg['dbfname']
      raise SystemExit, 2



    #get runtime settings
    self._parse_options()
    options = self.options

    if options.version:
      VERSION()
      raise SystemExit, 0
    elif options.help:
      USAGE()
      raise SystemExit, 0
    elif options.rm:
      self.del_note()
    elif options.clear:
      self.clear_notes()
    elif options.list:
      self.list_notes()
    elif options.iactive:
      self.interactive()

      #enable interactive mode history (if possible)
      histfile = os.path.join(os.path.expanduser('~'), cfg['histfile'])
      try:
        readline.read_history_file(histfile)
      except (NameError, IOError):
        pass
      else:
        try:
          import atexit
          atexit.register(readline.write_history_file, histfile)
          del histfile
        except:
          print >>sys.stderr, 'Cannot write history file for interactive mode.'

    elif options.show:
      self.show_note()
    else:
      self.add_note()



  def _create_cfg(self):
    TPL = r'''[general]
dbtype = dbhash
dbfilename = .notedb
prompt = note> 
time_format = %Y.%m.%d %H:%M:%S
note_format = [ %(timestamp)s ]\n%(lp)s. %(note)s\n
'''
    path = os.path.join(os.path.expanduser('~'), globals()['RCFILE'])
    try:
      fh = open(path, 'r')
    except (IOError, OSError):
      print >>sys.stderr, 'Cannot find (or read) config file (%s), trying to create one.' % path
      try:
        fh = open(path, 'w')
      except (IOError, OSError):
        print >>sys.stderr, "Cannot open config file to write (%s). Try to do it manually, example config:\n%s" % (path, TPL)
        return False
      else:
        fh.write(TPL)
        fh.close()
    return True
        

         
  def _parse_config(self, rcfile = None):
    if not rcfile:
      rcfile = os.path.join(os.path.expanduser(r'~'), r'%s' % globals()['RCFILE'])
    else:
      rcfile = os.path.expanduser(rcfile)
      
    if not self._create_cfg():
      raise SystemExit, 1

    cfg = ConfigParser.ConfigParser()
    cfg.read(rcfile)

    config = Container()
    config.dbtype       = cfg.get('general', 'dbtype')
    config.dbfname      = cfg.get('general', 'dbfilename')
    config.prompt       = cfg.get('general', 'prompt', raw = True) + ' '
    config.time_format  = cfg.get('general', 'time_format', raw = True)
    config.note_format  = cfg.get('general', 'note_format', raw = True).replace(r'\n', "\n")

    self.config = config
    return config



  def _parse_options(self, argv = None):
    if not argv:
      argv = sys.argv[1:]

    options = Container()
    options.add      = None
    options.rm       = None
    options.list     = None
    options.iactive  = None
    options.data     = None
    options.version  = None
    options.help     = None
    options.show     = None
    options.clear    = None

    #if called as 'inote.py', default mode is 'interactive'
    progname = os.path.basename(sys.argv[0])
    if   progname in ('inote', 'inote.py'):
      sh = 'hv'
      lo = ('help', 'version')

      #can safely set 'iactive' = True, cause when we parsing options in 'for' loop below,
      #there is _only_one_ loop.
      #and in __init__, options 'version' and 'help' are parsed as first in 'get runtime settings'
      options.iactive      = True

    #so if we're called as 'rnote.py', default mode is either 'list' or 'show'
    elif progname in ('rnote', 'rnote.py'):
      sh = 'lhvs'
      lo = ('list', 'help', 'version', 'show')

    #if nothing else, mode is set by switch, or is default 'add'
    else:
      sh = 'adclihvs'
      lo = ('add', 'del', 'list', 'iactive', 'help', 'version', 'clear', 'show')

    try:
      opts, args = getopt.gnu_getopt(argv, sh, lo)
    except getopt.GetoptError:
      USAGE()
      raise SystemExit, 2

    for o, a in opts:
      if   o in ('-h', '--help'):
        options.help      = True
      elif o in ('-v', '--version'):
        options.version   = True
      elif o in ('-s', '--show'):
        options.show      = True
      elif o in ('-l', '--list'):
        options.list      = True
      elif o in ('-a', '--add'):
        options.add       = True
      elif o in ('-i', '--iactive'):
        options.iactive   = True
      elif o in ('-d', '--del'):
        options.rm        = True
      elif o in ('-c', '--clear'):
        options.clear     = True
      break

    if progname in ('rnote', 'rnote.py'):
      if len(args) == 0:
        options.list       = True
      else:
        options.show       = True
        options.id         = args

    options.data          = args

    self.options = options
    #print "\n".join( [ '%s = %s' % (k.rjust(10), v) for k, v in options.getval().items() ] ); raise SystemExit
    return options.getval()


  
  def add_note(self, note = None):
    key = str(time.time())
    if note is None:
      note = ' '.join(self.options.data)
    if len(note) > 0:
      self.db[key] = note
    else:
      print >>sys.stderr, 'Can\'t add empty note.'
      USAGE()
      raise SystemExit, 7

  def del_note(self, id_notes = None):
    db = self.db
    if id_notes is not None:
      ids = id_notes
    else:
      ids = self.options.data

    keys = []
    for id in ids:
      try:
        id = int(id)
      except IndexError:
        print >>sys.stderr, 'Unknown note id (%s).' % id
      except TypeError:
        print >>sys.stderr, 'Note id must be an integer (%s).' % id
      else:
        lp = 1
        for k in sorted(db.keys()):
          if lp == id:
            keys.append(k)
            break
          lp += 1
    for key in keys:
      del db[key]
  
  def list_notes(self):
    db = self.db
    lp = 0
    note_format, time_format = self.config.getval('note_format', 'time_format')
    for k in sorted(db.keys()):
      timestamp = time.strftime(time_format, time.localtime(float(k)))
      note = db[k]
      lp += 1
      print note_format % locals()

  def interactive(self):
    self.start()

  def show_note(self, id_notes = None):
    db = self.db
    if id_notes is not None:
      ids = id_notes
    else:
      ids = self.options.data
    note_format, time_format = self.config.getval('note_format', 'time_format')

    if ids:
      for id in ids:
        try:
          id = int(id)
        except TypeError:
          print >>sys.stderr, 'Note id must be an integer.'
          USAGE()
          raise SystemExit, 4
        else:
          lp = 0
          for k in sorted(db.keys()):
            lp += 1
            if lp == id:
              timestamp = time.strftime(time_format, time.localtime(float(k)))
              note = db[k]
              print note_format % locals()
    else:
      self.list_notes()
    
  def clear_notes(self):
    self.db.clear()

# if ran as cli
if __name__ == '__main__':
  a = Note()

""" - domyslny tryb:
  - note.py  : add
  - rnote.py : list lub show, w zaleznosci od tego czy bedzie podane id czy nie
  - inote.py : interactive (jedyny)
"""
