# OCR Accuracy Benchmark Report

- Images tested: **14**
- Total queries: **42**
- Aggregate hit@1: **42/42 (100%)**
- Aggregate hit@5: **42/42 (100%)**
- Aggregate hit@10: **42/42 (100%)**

## Per-Image Summary

| Image | OCR Words | Indexed Entries | Queries | hit@1 | hit@5 | hit@10 |
|---|---:|---:|---:|---:|---:|---:|
| dataset real\WhatsApp Image 2026-04-04 at 01.14.53.jpeg | 203 | 242 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.19.48.jpeg | 81 | 141 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.22.14.jpeg | 48 | 90 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.22.18.jpeg | 43 | 80 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.22.25.jpeg | 82 | 89 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.22.34.jpeg | 143 | 143 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.22.49.jpeg | 65 | 167 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.25.47.jpeg | 170 | 392 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.25.59.jpeg | 35 | 35 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.26.06.jpeg | 44 | 78 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.26.24.jpeg | 135 | 234 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.27.02.jpeg | 29 | 53 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.27.23.jpeg | 29 | 56 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| dataset real\WhatsApp Image 2026-04-04 at 01.28.29.jpeg | 73 | 93 | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |

## Case Details

### dataset real\WhatsApp Image 2026-04-04 at 01.14.53.jpeg

- query=`file` expected=('file',) hit@1=True hit@5=True hit@10=True
  - 'File' score=1.00 box=(43,11,24,16)
  - 'files' score=1.00 box=(1306,381,42,20)
  - 'Mew File' score=1.00 box=(1265,445,62,14)
  - 'ingFileHandler' score=1.00 box=(654,197,70,18)
  - 'filenames/queries' score=1.00 box=(1390,468,42,20)
- query=`edit` expected=('edit',) hit@1=True hit@5=True hit@10=True
  - 'Edit' score=1.00 box=(81,11,28,16)
  - 'edit' score=1.00 box=(1347,468,42,20)
  - 'OPEN EDITORS' score=1.00 box=(69,79,86,14)
- query=`selection` expected=('selection',) hit@1=True hit@5=True hit@10=True
  - 'Selection' score=1.00 box=(119,11,60,16)
  - 'Ison' score=0.86 box=(1125,509,28,12)

### dataset real\WhatsApp Image 2026-04-04 at 01.19.48.jpeg

- query=`whatsapp` expected=('whatsapp',) hit@1=True hit@5=True hit@10=True
  - 'WhatsApp' score=1.00 box=(44,10,63,19)
- query=`02/04/2026 at 15.33` expected=('02/04/2026 at 15.33',) hit@1=True hit@5=True hit@10=True
  - '02/04/2026 at 15.33' score=1.00 box=(85,73,128,18)
- query=`nif65` expected=('nif65',) hit@1=True hit@5=True hit@10=True
  - 'nif65' score=1.00 box=(704,120,114,48)

### dataset real\WhatsApp Image 2026-04-04 at 01.22.14.jpeg

- query=`raju` expected=('raju',) hit@1=True hit@5=True hit@10=True
  - 'Raju' score=1.00 box=(418,74,65,33)
  - 'RA' score=1.00 box=(152,878,40,24)
- query=`institute` expected=('institute',) hit@1=True hit@5=True hit@10=True
  - 'Institute' score=1.00 box=(484,74,65,33)
- query=`technology` expected=('technology',) hit@1=True hit@5=True hit@10=True
  - 'Technology' score=1.00 box=(614,74,65,33)

### dataset real\WhatsApp Image 2026-04-04 at 01.22.18.jpeg

- query=`tirupat` expected=('tirupat',) hit@1=True hit@5=True hit@10=True
  - 'TIRUPAT' score=1.00 box=(48,68,110,24)
  - 'TIRUPATI' score=1.00 box=(792,55,152,45)
  - 'iittirupati' score=1.00 box=(934,1478,106,32)
  - 'iit_tirupati' score=1.00 box=(492,1478,114,32)
- query=`indian` expected=('indian',) hit@1=True hit@5=True hit@10=True
  - 'INDIAN' score=1.00 box=(183,55,152,45)
- query=`institute` expected=('institute',) hit@1=True hit@5=True hit@10=True
  - 'INSTITUTE' score=1.00 box=(335,55,152,45)

### dataset real\WhatsApp Image 2026-04-04 at 01.22.25.jpeg

- query=`slno` expected=('slno',) hit@1=True hit@5=True hit@10=True
  - 'SlNo' score=1.00 box=(40,22,80,32)
- query=`roll.no` expected=('roll.no',) hit@1=True hit@5=True hit@10=True
  - 'Roll.No' score=1.00 box=(132,22,104,32)
- query=`name` expected=('name',) hit@1=True hit@5=True hit@10=True
  - 'Name' score=1.00 box=(352,24,84,30)

### dataset real\WhatsApp Image 2026-04-04 at 01.22.34.jpeg

- query=`sl.no` expected=('sl.no',) hit@1=True hit@5=True hit@10=True
  - 'Sl.No' score=1.00 box=(45,7,42,16)
- query=`roll no` expected=('roll no',) hit@1=True hit@5=True hit@10=True
  - 'Roll No' score=1.00 box=(95,5,58,18)
- query=`name` expected=('name',) hit@1=True hit@5=True hit@10=True
  - 'Name' score=1.00 box=(225,7,46,16)

### dataset real\WhatsApp Image 2026-04-04 at 01.22.49.jpeg

- query=`whatsapp` expected=('whatsapp',) hit@1=True hit@5=True hit@10=True
  - 'WhatsApp' score=1.00 box=(44,10,63,19)
- query=`2428-cse` expected=('2428-cse',) hit@1=True hit@5=True hit@10=True
  - '2428-CSE' score=1.00 box=(533,51,82,20)
- query=`chats` expected=('chats',) hit@1=True hit@5=True hit@10=True
  - 'Chats' score=1.00 box=(86,60,66,26)
  - 'chat' score=1.00 box=(299,119,32,20)
  - 'at' score=1.00 box=(725,442,31,21)

### dataset real\WhatsApp Image 2026-04-04 at 01.25.47.jpeg

- query=`technology` expected=('technology',) hit@1=True hit@5=True hit@10=True
  - 'Technology' score=1.00 box=(686,2,227,57)
  - 'Technology' score=1.00 box=(159,83,52,12)
- query=`edition` expected=('edition',) hit@1=True hit@5=True hit@10=True
  - 'Edition' score=1.00 box=(496,51,53,20)
- query=`showcase` expected=('showcase',) hit@1=True hit@5=True hit@10=True
  - 'Showcase' score=1.00 box=(657,51,53,20)
  - 'SHOWCASE 2026' score=1.00 box=(1011,68,250,40)
  - 'Shows' score=0.89 box=(31,694,40,19)

### dataset real\WhatsApp Image 2026-04-04 at 01.25.59.jpeg

- query=`code like a pro` expected=('code like a pro',) hit@1=True hit@5=True hit@10=True
  - 'Code Like A Pro' score=1.00 box=(165,7,603,85)
- query=`for free` expected=('for free',) hit@1=True hit@5=True hit@10=True
  - 'For Free' score=1.00 box=(370,101,297,68)
- query=`html` expected=('html',) hit@1=True hit@5=True hit@10=True
  - 'HTML' score=1.00 box=(319,239,124,42)

### dataset real\WhatsApp Image 2026-04-04 at 01.26.06.jpeg

- query=`blockchain` expected=('blockchain',) hit@1=True hit@5=True hit@10=True
  - 'BLOCKCHAIN' score=1.00 box=(17,26,170,44)
  - 'BLOCKCHAIN' score=1.00 box=(65,201,336,44)
  - 'blockchain' score=1.00 box=(581,257,86,18)
  - 'Blockchaln' score=0.90 box=(345,315,53,18)
- query=`india` expected=('india',) hit@1=True hit@5=True hit@10=True
  - 'INDIA' score=1.00 box=(187,26,170,44)
  - 'Indian' score=1.00 box=(476,236,46,24)
  - 'INDIA Challenge' score=1.00 box=(62,252,375,57)
  - 'for a Better Indial' score=1.00 box=(64,982,196,26)
- query=`challenge` expected=('challenge',) hit@1=True hit@5=True hit@10=True
  - 'Challenge' score=1.00 box=(357,26,170,44)
  - 'INDIA Challenge' score=1.00 box=(62,252,375,57)
  - 'challenge cdac in' score=1.00 box=(63,891,183,30)

### dataset real\WhatsApp Image 2026-04-04 at 01.26.24.jpeg

- query=`file` expected=('file',) hit@1=True hit@5=True hit@10=True
  - 'File' score=1.00 box=(43,11,24,16)
- query=`edit` expected=('edit',) hit@1=True hit@5=True hit@10=True
  - 'Edit' score=1.00 box=(81,11,28,16)
  - 'OPEN EDITORS' score=1.00 box=(69,79,86,14)
- query=`selection` expected=('selection',) hit@1=True hit@5=True hit@10=True
  - 'Selection' score=1.00 box=(119,11,60,16)

### dataset real\WhatsApp Image 2026-04-04 at 01.27.02.jpeg

- query=`edit` expected=('edit',) hit@1=True hit@5=True hit@10=True
  - 'Edit' score=1.00 box=(41,19,26,14)
- query=`certificate jpeg` expected=('certificate jpeg',) hit@1=True hit@5=True hit@10=True
  - 'certificate jpeg' score=1.00 box=(757,19,88,16)
- query=`google developer groups` expected=('google developer groups',) hit@1=True hit@5=True hit@10=True
  - 'Google Developer Groups' score=1.00 box=(400,91,256,31)

### dataset real\WhatsApp Image 2026-04-04 at 01.27.23.jpeg

- query=`edit` expected=('edit',) hit@1=True hit@5=True hit@10=True
  - 'Edit' score=1.00 box=(41,19,26,14)
- query=`1765384280273.jpg` expected=('1765384280273.jpg',) hit@1=True hit@5=True hit@10=True
  - '1765384280273.jpg' score=1.00 box=(745,19,112,16)
- query=`remarkskill` expected=('remarkskill',) hit@1=True hit@5=True hit@10=True
  - 'Remarkskill' score=1.00 box=(632,140,160,30)
  - 'REMARKSKILL' score=1.00 box=(730,660,124,30)
  - 'Remark Skill Education' score=0.91 box=(382,668,198,24)

### dataset real\WhatsApp Image 2026-04-04 at 01.28.29.jpeg

- query=`sample` expected=('sample',) hit@1=True hit@5=True hit@10=True
  - 'sample' score=1.00 box=(73,13,43,18)
  - 'Sample' score=1.00 box=(321,15,35,16)
  - 'Sample Letterhead' score=1.00 box=(589,127,233,32)
  - 'com/sample-reports' score=1.00 box=(266,59,105,18)
- query=`hospital` expected=('hospital',) hit@1=True hit@5=True hit@10=True
  - 'hospital' score=1.00 box=(116,13,43,18)
- query=`patient` expected=('patient',) hit@1=True hit@5=True hit@10=True
  - 'patient' score=1.00 box=(159,13,43,18)

