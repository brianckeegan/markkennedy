#!/usr/bin/env python3

import re
import pandas as pd
import numpy as np
from dateutil.parser import parse as parse_time

COLUMNS = 'Category Attendance Affiliation Constituency Ranking Comments Time'.split()

def clean(lines):
    s = ' '.join(lines).strip()
    return s.replace('alumn us', 'alumnus').replace('Administratio n', 'Administration')

class Record:
    def __init__(self, headline, category):
        self.category = category
        self.attendance = []
        self.affiliation = []
        self.constituency = []
        self.ranking = []
        self.comments = []
        self.time = []
        offsets = []
        lastoffset = -1
        for head in re.split('\s{2,}', headline):
            lastoffset += 1 + headline[lastoffset+1:].find(head)
            offsets.append(lastoffset)
        if offsets[4] > 100: # repair missing ranking
            offsets.insert(3, 51)
        offsets[3] -= 1
        offsets[4] -= 3 # Some start with a space
        self.offsets = np.array(offsets)

    def as_tuple(self):
        self.ranking = ' '.join(self.ranking).split()
        return [self.category] + [clean(t) for t in (self.attendance, self.affiliation, self.constituency, self.ranking, self.comments)] + [parse_time(clean(self.time))]

    def __repr__(self):
        return str(dict(zip(COLUMNS, self.as_tuple())))

    def is_spam(self):
        comments = clean(self.comments)
        if ('best dinner recipes of all time foods that' in comments
            or 'how to make vodka inexpensive meals for large' in comments):
            return True
        return False
        

def read_txt(filename='3-4-30-2019-feedback-commentspdf.txt'):
    page_num = re.compile('^[0-9]{1,4}$')
    category_line = re.compile('^\s*Attendance')
    with open(filename, 'r') as f:
        records = []
        for line in f:
            if line.startswith('\x0c'): # new page
                new_page = True
                continue
            if page_num.match(line.strip()): # page number
                continue
            if category_line.match(line):
                category = re.split('\s{2,}', line.strip())[4]
                assert category.endswith('Comments:') or category.endswith('Comments'), 'split: {}'.format(re.split("\s{2,}", line))
                category = category.split()[0]
                continue
            if (line.startswith('Open') or line.startswith('Small group') or line.startswith('Private meeting')
                or line.startswith('Social') or line.startswith('Media/Social') or line.startswith('Other')
                or re.match('\s{10,25}(CU Boulder|CU Colorado|CU Denver|CU Anschutz|System|Not affiliated|\(blank\))', line)):
                rec = Record(line, category)
                records.append(rec)
                new_page = False
            else:
                assert (line.startswith(' ') or line.startswith('forum/Livestream') or line.startswith('meeting')
                      or line.startswith('gathering/recep') or line.startswith('on\n') or line.startswith('on ')
                      or line.startswith('media') or line == '\n')
            if new_page:
                indent = len(line) - len(line.lstrip())
                idx = rec.offsets.searchsorted(indent)
                if indent - rec.offsets[idx-1] < rec.offsets[idx] - indent:
                    rec.offsets[idx-1:] += indent - rec.offsets[idx-1] - 1
                else:
                    rec.offsets[idx:] -= rec.offsets[idx] - indent + 1
                new_page = False
            rec.attendance.append(line[:rec.offsets[1]].strip())
            rec.affiliation.append(line[rec.offsets[1]:rec.offsets[2]].strip())
            rec.constituency.append(line[rec.offsets[2]:rec.offsets[3]].strip())
            rec.ranking.append(line[rec.offsets[3]:rec.offsets[4]].strip())
            rec.comments.append(line[rec.offsets[4]:rec.offsets[5]].strip())
            if False:
                print(repr(line))
                print(rec.offsets)
            if len(rec.time) < 2:
                # time is only two lines, but a subsequent page might change the field widths
                rec.time.append(line[rec.offsets[5]:].strip())
                if len(rec.time) == 2:
                    rec.offsets[5] = 200

    df = pd.DataFrame([r.as_tuple() for r in records if not r.is_spam()], columns=COLUMNS)
    return df

if __name__ == '__main__':
    df = read_txt()
