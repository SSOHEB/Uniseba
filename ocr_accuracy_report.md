# OCR Accuracy Benchmark Report

- Images tested: **1**
- Total queries: **5**
- Aggregate hit@1: **5/5 (100%)**
- Aggregate hit@5: **5/5 (100%)**
- Aggregate hit@10: **5/5 (100%)**

## Per-Image Summary

| Image | OCR Words | Indexed Entries | Queries | hit@1 | hit@5 | hit@10 |
|---|---:|---:|---:|---:|---:|---:|
| test_crop.png | 86 | 338 | 5 | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |

## Case Details

### test_crop.png

- query=`contents` expected=('contents',) hit@1=True hit@5=True hit@10=True
  - 'Contents' score=1.00 box=(67,21,80,20)
- query=`biography` expected=('biography',) hit@1=True hit@5=True hit@10=True
  - 'Biography' score=1.00 box=(63,101,87,28)
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
- query=`references` expected=('references',) hit@1=True hit@5=True hit@10=True
  - 'References' score=1.00 box=(67,827,94,20)
  - 'referred' score=0.86 box=(644,220,54,28)

