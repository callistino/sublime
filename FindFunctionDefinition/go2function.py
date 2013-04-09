import sublime, sublime_plugin
import tempfile, os, sys
import subprocess
import re
import functools
import os

# Borrowed from FollowFunctionPHP and find-function-definition
# plugin pachages

# File DB to store undo locations.
  def grepDb(self, filename):
    isresult = None
    files = []
    if os.path.isfile(filename):
      for n, line in enumerate(open(filename)):
        if self.word.decode('utf-8') in line.decode('utf-8'):
          tmpline = line.split(";")
          if tmpline[1] != "":
            res = []
            res.append(tmpline[0])
            if len(tmpline[1]) > 50:
              tmplen = len(tmpline[1])-46
              # res.append(tmpline[1][:7] + "..." + tmpline[1][tmplen:])
              res.append("..." + tmpline[1][tmplen:])
            else:
              res.append(tmpline[1])
            self.viewResultfiles.append(res)
            self.resultfiles.append(tmpline[1])
            isresult = 1
    else:
      print "Brak indeksu"
      sublime.status_message('Please reindex files')
    return isresult

  # Save file and location from where the definition is called.
  def saveUndo(self):
    for region in self.view.sel():
      column = self.view.rowcol(region.begin())[1] + 1
      row = self.view.rowcol(region.begin())[0] + 1
      # (row,col) = self.view.rowcol(self.view.sel()[0].begin())

    undoFilename = self.view.file_name() + ":" + str(row) + ":" + str(column)
    filename = os.path.join(sublime.packages_path(), self.pathForDB, "undo")
    if os.path.isfile(filename) == False:
      with open(filename, 'w') as f:
        f.write(undoFilename.decode('utf-8') + "\n")
      f.close()
    else:
      with open(filename, 'r+') as f:
        lineCnt = sum(1 for line in f)
        if lineCnt > 4 :
          f.seek(0,0)
          lines = f.readlines()
          # print lines
          f.close
          with open(filename, 'w') as f:
            for (cnt, line) in enumerate(lines):
              if cnt > (lineCnt-4-1):
                f.write(line)
            f.write(undoFilename.decode('utf-8') + "\n")
          f.close()
        else:
          f.write(undoFilename.decode('utf-8') + "\n")
          f.close()

#borrowed from Git Plugin by David Lynch
#https://github.com/kemayo/sublime-text-2-git/
def do_when(conditional, callback, *args, **kwargs):
  if conditional():
      return callback(*args, **kwargs)
  sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)

#Gets current word and performs a grep on project folders
#to see if it has a function definition or not
class GoToFunctionCommand(sublime_plugin.TextCommand):
  resultfiles = []
  viewResultfiles = []
  dbPath = ""
  word = ""

  def run(self, text):
    view = self.view

    #get current word
    selection_region = view.sel()[0]
    word_region = view.word(selection_region)
    word = view.substr(word_region).strip()
    word = re.sub('[\(\)\{\}\s]', '', word)

    #get folders to search
    window = sublime.active_window()
    proj_folders = window.folders()
    nodir = self.getExcludedDirs(view)

    if word != "":
      print "[Go2Function] Searching for 'function "+word+"'..."

      for dir in proj_folders:
        resp = self.doGrep(word, dir, nodir)

        if len(resp) > 0:
          self.openFileToDefinition(resp)
          break

      #if not found show error (ie loop ends without a break)
      else:
        print "[Go2Function] "+word+" not found"
        sublime.error_message("could not find function definition for "+word)

  #actually do the grep
  #well, actually use the native python functions, not grep...
  def doGrep(self, word, directory, nodir):
    out = ()
    terms = self.getSearchTerms(word)

    for r,d,f in os.walk(directory):
      if self.canCheckDir(r, nodir):
        for files in f:
          fn = os.path.join(r, files)
          search = open(fn, "r")
          lines = search.readlines()

          for n, line in enumerate(lines):
            for find in terms:
              if find in line:
                out = (fn, n)
                break

          search.close()

          if len(out) > 0:
            break

        if len(out) > 0:
          break

    return out

  def getSearchTerms(self, word):
    wordstr = str(word)

    #search for normal functions and named anonymous functions
    lookup1 = "function "+wordstr
    lookup2 = wordstr+": function"
    lookup3 = wordstr+":function"
    lookup4 = wordstr+" :function"
    lookup5 = wordstr+" = function"
    lookup6 = wordstr+"= function"
    lookup7 = wordstr+"=function"
    lookup8 = wordstr+" =function"

    return (lookup1, lookup2, lookup3, lookup4, lookup5, lookup6, lookup7, lookup8)

  def getExcludedDirs(self, view):
    #this gets the folder_exclude_patterns from the settings file, not the project file
    dirs = view.settings().get("folder_exclude_patterns", [".git", ".svn", "CVS", ".hg"]) #some defaults
    return dirs

  def canCheckDir(self, dir, excludes):
    count = 0

    #potentially quite expensive - better way?
    for no in excludes:
      if no not in dir:
        count = count + 1

    if count == len(excludes):
      return True
    else:
      return False

  #open the file and scroll to the definition
  def openFileToDefinition(self, response):
    file, line = response

    print "[Go2Function] Opening file "+file+" to line "+str(line)

    line = line - 1

    selectedFile = os.path.normpath(self.resultfiles[num])
    fileWithPosition = self.grep(selectedFile)
    self.saveUndo()

    window = sublime.active_window()
    new_view = window.open_file(file)

    do_when(
      lambda: not new_view.is_loading(),
      lambda: new_view.set_viewport_position(new_view.text_to_layout(new_view.text_point(line, 0)))
    )