def get_sixteenths(token):
    if token == 'quadruple_whole':
        return 64
    elif token == 'double_whole':
        return 32
    elif token == 'whole':
        return 16
    elif token == 'half':
        return 8
    elif token == 'quarter':
        return 4
    elif token == 'eighth':
        return 2
    elif token == 'sixteenth':
        return 1
    elif token == 'thirty_second':
        return 0.5
    elif token == 'sixty_fourth':
        return 0.25
    return 0

def parse_time_sig(time_sig):
    time_sig = time_sig.split('-')[1]
    if time_sig == 'C':
        return 4, 4
    elif time_sig == 'C/':
        return 2, 2
    elif '/' in time_sig:
        top, bottom = time_sig.split('/')
        return int(top), int(bottom)
    else:
        return 4, 4
    
def time_sig_to_sixteenths(time_sig):
    top, bottom = parse_time_sig(time_sig)
    return (16 // bottom) * top

def token_to_action(token):
    if token in ['barline', '</s>', '<s>']:
        return ("RESET", 0)
    elif token == 'dot':
        return ("USE_LAST_DURATION", 0.5)
    elif token == 'dotdot':
        return ("USE_LAST_DURATION", 0.25)
    elif len(token) > 14 and token[:14] == 'timeSignature-':
        return ("SET_TIMESIG", time_sig_to_sixteenths(token))
    else:
        return ("DECREMENT", get_sixteenths(token))
    
def is_rhythmically_coherent(tokens):
    timeSigs = [t for t in tokens if t[:4] == 'time']
    if len(timeSigs) > 1:
        return False
    sixteenths_left = 0
    sixteenths_per_bar = 0
    last_duration = 0
    anacrusis = True
    for token in tokens:
        if token[0] == '<':
            continue
        action, data = token_to_action(token)
        if token == "barline":
            if sixteenths_left != 0 and not anacrusis:
                return False
            anacrusis = False
        if action == "RESET":
            sixteenths_left = sixteenths_per_bar 
            last_duration = 0
        elif action == "USE_LAST_DURATION":
            sixteenths_left -= data * last_duration
        elif action == "SET_TIMESIG":
            sixteenths_per_bar = data
            sixteenths_left = data
        elif action == "DECREMENT":
            sixteenths_left -= data
            last_duration = data
    return True
    