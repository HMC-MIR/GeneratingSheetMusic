#!/usr/bin/env python
# coding: utf-8

# In[1]:


import re
import json


# In[2]:


# Key signature to sharps and flats
translate_key = {
    'CM': '',
    'FM': 'bB',
    'BbM': 'bBE',
    'EbM': 'bBEA',
    'AbM': 'bBEAD',
    'DbM': 'bBEADG',
    'GbM': 'bBEADGC',
    'FxM': 'xFCGDAE',
    'BM': 'xFCGDA',
    'EM': 'xFCGD',
    'AM': 'xFCG',
    'DM': 'xFC',
    'GM': 'xF'
}

# Simple cases for duration to integer
translate_duration_dict = {
    'quadruple_whole': '0',
    'double_whole': '9',
    'whole': '1',
    'half': '2',
    'quarter': '4',
    'eighth': '8',
    'sixteenth': '6',
    'thirty_second': '3',
    'sixty_fourth': '5'
}

# Simple cases for duration to integer
duration_to_sfs = {
    'quadruple_whole': 256,
    'double_whole': 128,
    'whole': 64,
    'half': 32,
    'quarter': 16,
    'eighth': 8,
    'sixteenth': 4,
    'thirty_second': 2,
    'sixty_fourth': 1
}

def timesig_to_sfs(timesig):
    if timesig == 'c':
        return 16, 64
    elif timesig == 'c/':
        return 32, 64
    else:
        numer = int(timesig.split('/')[0])
        denom = int(timesig.split('/')[1])
        sfs_per_beat = 64 // denom
        sfs_per_bar = sfs_per_beat * numer
        return sfs_per_beat, sfs_per_bar


# In[3]:


def parse_pitch(pitch):
    # Octave is last character
    octave = int(pitch[-1])
    return octave, pitch[:-1]

def translate_octave(octave):
    # ' is octave of middle C, '' is two octaves above; opposite for comma
    if octave < 4:
        return ',' * (4 - octave)
    else:
        return "'" * (octave - 3)


# In[4]:


def pseudo_semantic_to_semantic(semantic):
    semantic = re.sub('note (.*?) ', r'note-\1_', semantic)
    semantic = re.sub('rest ', r'rest-', semantic)
    semantic = re.sub(' fermata', r'_fermata', semantic)
    semantic = re.sub(' dotdot', '..', semantic)
    semantic = re.sub(' dot', '.', semantic)
    return semantic.strip()


# In[5]:


BEAM_DURATIONS = ["eighth", "sixteenth", "thirty_second", "sixty_fourth"]


# In[6]:


def parse_clef(symbol):
    clef = symbol.split('-')[1]
    # If clef is something like G2, PAE wants G-2
    if len(clef) == 2:
        clef = clef[0] + '-' + clef[1]
    return clef


# In[7]:


def parse_timesig(symbol):
    timesig = symbol.split('-')[1].lower()
    sfs_per_beat, sfs_per_bar = timesig_to_sfs(timesig)
    return timesig, sfs_per_beat, sfs_per_bar


# In[8]:


def parse_note(symbol, keysig):
    dots = 0
    isGrace = False
    isFermata = False
    data = ''
    # If gracenote, take out grace and add "q" to data
    if symbol[:5] == 'grace':
        symbol = symbol[5:]
        isGrace = True
    # Keep track of number of dots
    while symbol[-1] == '.':
        dots += 1
        symbol = symbol[:-1]
    if len(symbol) >= 8 and symbol[-8:] == '_fermata':
        symbol = symbol[:-8]
        isFermata = True
    # Pitch comes after - and before _
    pitch = symbol.split('-')[1].split('_')[0]
    # Duration is everything after _ (can have another _, like thirty_second)
    duration = '_'.join(symbol.split('_')[1:])
    duration_sfs = int(duration_to_sfs[duration] * (1.5 ** dots)) if not isGrace else 0
    octave, pitch = parse_pitch(pitch)
    data += translate_octave(octave)
    data += translate_duration_dict[duration]
    # Add dots
    data += '.' * dots
    if isGrace:
        data += 'q'
    if isFermata:
        data += '('
    # If the accidental is already included in the time signature, just use letter name
    if pitch[0] in keysig and len(pitch) > 1 and pitch[-1] == keysig[0]:
        data += pitch[0]
    # If the pitch is in the key signature but doesn't have an accidental, mark as natural
    elif pitch[0] in keysig and len(pitch) == 1:
        data += 'n' + pitch
    else:
        data += pitch[::-1]
    if isFermata:
        data += ')'
    return data, duration_sfs


# In[15]:


def parse_rest(symbol):
    data = ''
    isFermata = False
    dots = 0
    # Duplicate code from note
    while symbol[-1] == '.':
        dots += 1
        symbol = symbol[:-1]
    if len(symbol) >= 8 and symbol[-8:] == '_fermata':
        symbol = symbol[:-8]
        isFermata = True
    duration = symbol.split('-')[1]
    duration_sfs = int(duration_to_sfs[duration] * (1.5 ** dots))
    
    data += translate_duration_dict[duration]
    
    data += '.' * dots
    # Symbol for rest
    data += '-' if not isFermata else '(-)'
    return data, duration_sfs


# In[10]:


def insert_beams(data_pieces, sfs_per_beat, sfs_per_bar):
    data = ''
    breakpoints = list(range(0, sfs_per_bar, sfs_per_beat))
    breakpoints_eighth = [sfs_per_bar // 2]
    location_sfs = 0
    inBeam = False
    justStartedBeam = False
    for i, (data_piece, sfs) in enumerate(data_pieces):
        worthy_of_beam = '-' not in data_piece and sfs < 16 and sfs != 0
        is_eighth = 8 <= sfs < 16
        is_breakpoint = not is_eighth and location_sfs in breakpoints or location_sfs in breakpoints_eighth
        
        # If in a beam, end beam BEFORE ADDING TOKEN if:
        # This token is a rest
        # OR This token is a quarter note or slower
        # OR This token does not have rhythmic value (includes barline)
        # OR This token is on a breakpoint
        if inBeam and (not worthy_of_beam or is_breakpoint):
            inBeam = False
            if not justStartedBeam:
                data += '}'
            else:
                # Just started a beam, remove last {
                data = data[::-1].replace('{', '', 1)[::-1]
        
        # If not in a beam, start beam BEFORE ADDING TOKEN if:
        # This token is not a rest
        # AND This token is faster than a quarter note
        # AND This token has rhythmic value
        if not inBeam and worthy_of_beam:
            inBeam = True
            justStartedBeam = True
            data += '{'
        else:
            justStartedBeam = False
            
        data += data_piece
        location_sfs += sfs
        
        if data_piece == '/':
            location_sfs = 0
    if inBeam:
        data += '}'
    return data


# In[11]:


def convert(semantic):
    # PAE uses x for sharp
    semantic = re.sub('#', 'x', semantic)
    semantic_split = semantic.split()
    clef = ''
    keysig = ''
    timesig = ''
    data = ''
    data_pieces = []
    inBeams = False
    sfs_per_beat = 0
    sfs_per_bar = 0
    # Number of dots to add at some point
    dots = 0
    for i, symbol in enumerate(semantic_split):
        data = ''
        duration_sfs = 0
        # Clef
        if len(symbol) >= 4 and symbol[:4] == 'clef':
            clef = parse_clef(symbol)
            continue
        # Key signature
        elif len(symbol) >= 3 and symbol[:3] == 'key':
            keysig = translate_key[symbol.split('-')[1]]
            continue
        # Time signature
        elif len(symbol) >= 4 and symbol[:4] == 'time':
            timesig, sfs_per_beat, sfs_per_bar = parse_timesig(symbol)
            continue
        # Note or gracenote (e.g. note-C4_quarter. => 4.'C)
        elif len(symbol) >= 5 and symbol[:4] == 'note' or symbol[:5] == 'grace':
            parsed, duration_sfs = parse_note(symbol, keysig)
            data += parsed
        # Rest (e.g. rest-quarter => 4-)
        elif len(symbol) >= 4 and symbol[:4] == 'rest':
            parsed, duration_sfs = parse_rest(symbol)
            data += parsed
        # Barline (barline => /)
        elif symbol == 'barline':
            data += '/'
        # Multirest (e.g. multirest-11 => =11)
        elif len(symbol) >= 5 and symbol[:5] == 'multi':
            data += '=' + symbol.split('-')[1]
        # Tie (tie => +)
        elif symbol == 'tie':
            data += '+'
        data_pieces.append((data, duration_sfs))
    data = insert_beams(data_pieces, sfs_per_beat, sfs_per_bar)
    # Return data object
    obj = {
        "clef": clef,
        "keysig": keysig,
        "timesig": timesig,
        "data": data
    }
    return obj

def convert_and_save(semantic, filename):
    data = convert(semantic)
    json.dump(data, open(filename, 'w'))

