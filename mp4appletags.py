#!/usr/bin/env python
#encoding:utf-8
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)
 
"""
mp4movietags.py
Automatic Movie tagger.

thanks goes to:
the MP4v2 team (http://code.google.com/p/mp4v2/) for their excellent mp4 container editing library
the Subler team (http://code.google.com/p/subler/), their project was used as a template for MP4Tagger (source code soon to be released)
"""

__author__ = ""
__version__ = ""
 
import os
import sys
import re
from optparse import OptionParser
import itunes
from mp4v2.mp4file import *
from datetime import datetime

def openurl(urls):
    for url in urls:
        if len(url) > 0:
            os.popen("open \"%s\"" % url)
        #end if len
    #end for url
    return
#end openurl

def getDataFromApple(opts, movieName, movieYear):
    """docstring for getDataFromApple"""
    if opts.verbose == 2:
        print "!!Looking up data for: %s - %s" % (movieName, movieYear)
    #end if debug
    movieResults = itunes.search_movie(movieName.decode('utf-8'))
    movies = []
    
    if opts.verbose == 2:
        print "!!Search returned %s hits" % len(movieResults)
    #end if debug
    
    #we got zero hits, try replacing some commonly used replacement-characters due to filename illegality
    if len(movieResults) < 1:
        if movieName.count(';'):
            tempMovieName = movieName.replace(';', ':')
            return getDataFromApple(opts, tempMovieName, movieYear)
        elif movieName.count('_'):
            tempMovieName = movieName.replace('_', ' ')
            return getDataFromApple(opts, tempMovieName, movieYear)
        else:
            #last ditch attempt, search for movies by longest word in movie name as long as more then one word
            if len(movieName.split()) < 2:
                return movies
            #end if len
            movieNameLongestWord = max(movieName.split(), key=len)
            longestWordMovies = getDataFromApple(opts, movieNameLongestWord, movieYear)
            if opts.interactive or len(longestWordMovies) == 1:
                if opts.verbose == 2:
                    print "!!Using search result(s) based upon longest word search"
                #end if debug
                return longestWordMovies
            #end if interactive
            return movies
        #end if count
    #end if len
    
    if movieYear != "":
        for movieResult in movieResults:
            #check that the year tag in the file name matches with the release date, otherwise not the movie we are looking for
            if opts.verbose == 2:
                print "!!Potential hit: %s" % movieResult.name
            if movieResult.kind != "feature-movie":
                continue
            if movieResult.release_date:
                if movieResult.release_date.startswith(movieYear) or movieResult.release_date.startswith(str(int(movieYear)+1)):
                    movie = itunes.lookup(movieResult.id)
                    movies.append(movie)
        #end for movie
    else:
        for movieResult in movieResults:
            #check that the year tag in the file name matches with the release date, otherwise not the movie we are looking for
            if opts.verbose == 2:
                print "!!Potential hit: %s" % movieResult.name
            if movieResult.kind != "feature-movie":
                continue
            if movieResult.release_date:
                movie = itunes.lookup(movieResult.id)
                movies.append(movie)
        #end for movie
    return movies
#end getDataFromApple


def tagFile(opts, movie, fileName, MP4Tagger):
    """docstring for tagFile"""
    if opts.verbose > 0:
        print "  Tagging file..."
    #end if verbose
    
    #setup tags for the MP4Tagger function
    addContentID = " -contentid %s" % movie.id

    #Create the command line string
    tagCmd = MP4Tagger + addContentID + " \"" + fileName.replace('"', '\\"') + "\"" 
    
    tagCmd = tagCmd.replace('`', "'")
    
    if opts.verbose == 2:
        print "!!Tag command: %s" % unicode(tagCmd).encode("utf-8")
    #end if debug
    
    #run MP4Tagger using the arguments we have created
    result = os.popen(tagCmd.encode("utf-8")).read()
    if result.count("Program aborted") or result.count("Error") or result.count("Segmentation fault"):
        print "** ERROR: %s" % result
        return
    
    if opts.verbose > 0:
        print "  Tagged: " + fileName
    
#end tagFile

def alreadyTagged(opts, MP4Tagger, fileName):
    """docstring for checkIfAlreadyTagged"""
    #check if file has already been tagged
    cmd = "\"" + MP4Tagger + "\" -i \"" + fileName + "\"" + " -t"
    existingTagsUnsplit = os.popen(cmd).read()
    existingTags = existingTagsUnsplit.split('\r')
    for line in existingTags:
        if line.count("Comments: tagged by mp4movietags"):
            if opts.verbose > 0:
                print "  Already tagged. Skipping..."
            #end if verbose
            return True
        #end if line.count
    #end for line
    if opts.verbose == 2:
        print "!!Not previously tagged"
    return False
#end checkIfAlreadyTagged

def createCommaSeperatedStringFromJobSpecificCastDict(dict):
    """docstring for createNameArrayFromJobSpecificCastDict"""
    result = ""
    for personID in dict:
        if result == "":
            result = dict[personID]['name']
        else:
            result = "%s, %s" % (result, dict[personID]['name'])
    return result
#end createNameArrayFromJobSpecificCastDict

def main(): 
    parser = OptionParser(usage="%prog [options] <path to moviefile>\n%prog -h for full list of options")
    
    parser.add_option(  "-b", "--batch", action="store_false", dest="interactive",
                        help="Selects first search result, requires no human intervention once launched")
    parser.add_option(  "-i", "--interactive", action="store_true", dest="interactive",
                        help="Interactivly select correct movie from search results [default]")
    parser.add_option(  "-c", "--cautious", action="store_false", dest="overwrite", 
                        help="Writes everything to new files. Nothing is deleted (will make a mess!)")
    parser.add_option(  "-d", "--debug", action="store_const", const=2, dest="verbose", 
                        help="Shows all debugging info")
    parser.add_option(  "-v", "--verbose", action="store_const", const=1, dest="verbose",
                        help="Will provide some feedback [default]")
    parser.add_option(  "-q", "--quiet", action="store_const", const=0, dest="verbose",
                        help="For ninja-like processing")
    parser.add_option(  "-f", "--force-tagging", action="store_true", dest="forcetagging",
                        help="Tags previously tagged files")
    parser.add_option(  "-t", "--no-tagging", action="store_false", dest="tagging",
                        help="Disables tagging")
    parser.add_option(  "-y", "--year", action="store_true", dest="year",
                        help="Disables the year detection and uses a user-provided value")
    parser.set_defaults( interactive=True, overwrite=True, debug=False, verbose=1, forcetagging=False,
                            removetags=False, tagging=True, year=False )
    
    opts, args = parser.parse_args()
    
    MP4Tagger = "mp4tags"
    
    if opts.overwrite:
        additionalParameters = " !!overWrite"
    else:
        additionalParameters = ""
    #end if opts.overwrite
    
    if len(args) == 0:
        parser.error("No file supplied")
    #end if len(args)
    
    if opts.year:
        year = args.pop(0)
        print "Using provided year: %s" % year

    if len(args) > 1:
        parser.error("Provide single file")
    #end if len(args)
    
    if not os.path.isfile(args[0]):
        sys.stderr.write(args[0] + " is not a valid file\n")
        return 1
    #end if not os.path.isfile
    
    if opts.verbose > 0:
        if opts.forcetagging:
            processingString = "Processing: %s [forced]" % args[0]
        else:
            processingString = "Processing: %s" % args[0]
        print processingString
    #end if opts.verbose > 0
    
    #switch to the directory that holds the movie we wish to tag
    os.chdir(os.path.abspath(os.path.dirname(args[0])))
    fileName = os.path.basename(args[0])
    (movieFileName, extension) = os.path.splitext(fileName)
    if not extension.count("mp4") and not extension.count("m4v"):
        sys.stderr.write("%s is of incorrect file type. Convert to h264 with extension mp4 or m4v\n" % fileName)
        return 2
    #end if not extension

    movieName = ""
    movieYear = ""

    mp4 = MP4File(fileName)
    if mp4 != None:
        movieName = mp4.name
        movieYear = str(mp4.releaseDate.year)
        del mp4
    
    yearWithBrackets = re.compile("\([0-9]{4}\)")
    yearWithoutBrackets = re.compile("[0-9]{4}")

    if opts.year:
        movieYear = year
        if movieName == "":
            movieName = movieFileName.replace(movieYear, '', 1).strip()
    else:
        try:
            if movieName == "":
                movieYear = yearWithBrackets.findall(movieFileName)
                if len(movieYear) > 0:
                    movieYear = movieYear[0]
                    movieName = movieFileName.replace(movieYear, '', 1).strip()
                    movieYear = yearWithoutBrackets.findall(movieYear)[0]
                else:
                    movieName = movieFileName.strip()
                    movieYear = ""
        except:
            sys.stderr.write("%s is of incorrect syntax. Example: \"Movie Name (YEAR).m4v\"" % fileName)
            return 3
        #end try
    
    #============ embed information in file using MP4Tagger ============
    if opts.tagging:
        
        #============ TAG DATA ============ 
        #download information from TMDb
        if opts.verbose > 0:
            print "  Retrieving data from Apple"
        #end if verbose
        movies = getDataFromApple(opts, movieName, movieYear)
        
        if len(movies) == 0:
            sys.stderr.write("  No matches found for \"" + movieName + "\" made in " + movieYear + "\n")
            return 4
        
        moviesPreview = []
        for movie in movies:
            moviesPreview.append(movie.url)
        #end for ids

        if opts.interactive and len(movies) > 1:
            print "  Potential Title Matches"
            movieCounter = 0
            for movie in movies:
                print "   %s. %s (Released: %s, ID: %s)" % (movieCounter, movie.name, movie.release_date, movie.id)
                movieCounter = movieCounter + 1
            #end for movie in movies
     
            #allow user to preview movies
            print "  Example of listing: 0 2 4, <CR> for all"
            moviePreviewRequestNumbers = raw_input("  List Movies to Preview: ")
            moviePreviewUrls = []
            if moviePreviewRequestNumbers:
                moviePreviewRequests = moviePreviewRequestNumbers.split()
    
                for artworkPreviewRequest in moviePreviewRequests:
                    moviePreviewUrls.append(moviesPreview[int(artworkPreviewRequest)])
            else:
                for i in range(0, len(moviesPreview)):
                    moviePreviewUrls.append(moviesPreview[i])

            #end for artworkPreviewRequest
            openurl(moviePreviewUrls)

            #ask user what movie he wants to use
            movieChoice = int(raw_input("  Select correct title: "))
        else:
            if opts.verbose > 0:
                print "  Autoselecting only movie option"
            movieChoice = 0
        #end if interactive
        
        movie = movies[movieChoice]
    
        tagFile(opts, movie, fileName, MP4Tagger)
    
    #end if opts.tagging
    return 0
    

if __name__ == "__main__":
    sys.exit(main())
