# OCR Accuracy Benchmark Report

- Images tested: **1**
- Total queries: **20**
- Aggregate hit@1: **20/20 (100%)**
- Aggregate hit@5: **20/20 (100%)**
- Aggregate hit@10: **20/20 (100%)**

## Per-Image Summary

| Image | OCR Words | Indexed Entries | Queries | hit@1 | hit@5 | hit@10 |
|---|---:|---:|---:|---:|---:|---:|
| test_crop.png | 86 | 338 | 20 | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |

## Case Details

### test_crop.png

- query=`contents` expected=('contents',) hit@1=True hit@5=True hit@10=True
  - 'Contents' score=1.00 box=(67,21,80,20)
- query=`biography` expected=('biography',) hit@1=True hit@5=True hit@10=True
  - 'Biography' score=1.00 box=(63,101,87,28)
- query=`early` expected=('early',) hit@1=True hit@5=True hit@10=True
  - 'Early life' score=1.00 box=(80,138,74,24)
  - 'Early journalistic' score=1.00 box=(80,232,134,24)
- query=`education` expected=('education',) hit@1=True hit@5=True hit@10=True
  - 'Education' score=1.00 box=(498,316,59,32)
  - 'education' score=1.00 box=(320,350,60,30)
  - 'Education' score=1.00 box=(320,380,58,32)
  - 'Education' score=1.00 box=(1373,691,59,20)
  - 'Education and' score=1.00 box=(81,175,116,20)
- query=`movement` expected=('movement',) hit@1=True hit@5=True hit@10=True
  - 'movement' score=1.00 box=(758,254,62,28)
  - 'movement' score=1.00 box=(95,369,88,18)
  - 'Movement' score=1.00 box=(97,425,88,20)
  - 'Movement' score=1.00 box=(97,516,86,20)
  - 'Movement' score=1.00 box=(574,533,50,29)
- query=`notes` expected=('notes',) hit@1=True hit@5=True hit@10=True
  - 'Notes' score=1.00 box=(67,791,50,20)
  - 'Not' score=1.00 box=(354,148,47,24)
- query=`references` expected=('references',) hit@1=True hit@5=True hit@10=True
  - 'References' score=1.00 box=(67,827,94,20)
  - 'referred' score=0.86 box=(644,220,54,28)
- query=`history` expected=('history',) hit@1=True hit@5=True hit@10=True
  - 'View history' score=1.00 box=(1328,17,101,30)
- query=`source` expected=('source',) hit@1=True hit@5=True hit@10=True
  - 'View source' score=1.00 box=(1215,21,98,20)
- query=`gandhi` expected=('gandhi',) hit@1=True hit@5=True hit@10=True
  - 'Gandhi' score=1.00 box=(496,567,58,28)
  - "Gandhi's" score=1.00 box=(923,596,54,33)
  - "Gandhi's" score=1.00 box=(937,664,56,28)
  - 'and' score=1.00 box=(536,220,54,28)
  - 'and' score=1.00 box=(821,254,62,28)
- query=`nehru` expected=('nehru',) hit@1=True hit@5=True hit@10=True
  - 'Nehru' score=1.00 box=(1333,780,69,24)
- query=`jamia` expected=('jamia',) hit@1=True hit@5=True hit@10=True
  - 'Jamia' score=1.00 box=(320,845,49,31)
  - 'Islamia' score=0.89 box=(418,845,49,31)
- query=`legacy` expected=('legacy',) hit@1=True hit@5=True hit@10=True
  - 'Legacy and influence' score=1.00 box=(63,717,175,26)
- query=`azad` expected=('azad',) hit@1=True hit@5=True hit@10=True
  - 'Azad' score=1.00 box=(476,114,61,28)
  - 'Azad' score=1.00 box=(1027,114,61,28)
  - 'Azad' score=1.00 box=(591,148,47,24)
  - 'Azad' score=1.00 box=(914,220,54,28)
  - 'Azad' score=1.00 box=(508,436,47,30)
- query=`abdul` expected=('abdul',) hit@1=True hit@5=True hit@10=True
  - 'Abdul' score=1.00 box=(829,148,47,24)
  - 'Abdul Kalam Azad' score=1.00 box=(1216,204,198,26)
  - 'Abul Kalam Ghulam' score=0.89 box=(322,190,194,24)
- query=`educ` expected=('education',) hit@1=True hit@5=True hit@10=True
  - 'Education' score=1.00 box=(498,316,59,32)
  - 'education' score=1.00 box=(320,350,60,30)
  - 'Education' score=1.00 box=(320,380,58,32)
  - 'Education' score=1.00 box=(1373,691,59,20)
  - 'Education and' score=1.00 box=(81,175,116,20)
- query=`move` expected=('movement',) hit@1=True hit@5=True hit@10=True
  - 'movement' score=1.00 box=(758,254,62,28)
  - 'movement' score=1.00 box=(95,369,88,18)
  - 'Movement' score=1.00 box=(97,425,88,20)
  - 'Movement' score=1.00 box=(97,516,86,20)
  - 'Movement' score=1.00 box=(574,533,50,29)
- query=`refer` expected=('references',) hit@1=True hit@5=True hit@10=True
  - 'References' score=1.00 box=(67,827,94,20)
  - 'referred' score=1.00 box=(644,220,54,28)
  - 'career' score=0.89 box=(83,257,54,16)
  - 'career' score=0.89 box=(83,615,54,16)
- query=`gand` expected=('gandhi',) hit@1=True hit@5=True hit@10=True
  - 'Gandhi' score=1.00 box=(496,567,58,28)
  - "Gandhi's" score=1.00 box=(923,596,54,33)
  - "Gandhi's" score=1.00 box=(937,664,56,28)
  - 'and' score=1.00 box=(536,220,54,28)
  - 'and' score=1.00 box=(821,254,62,28)
- query=`nehr` expected=('nehru',) hit@1=True hit@5=True hit@10=True
  - 'Nehru' score=1.00 box=(1333,780,69,24)

