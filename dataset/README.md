# Dataset Folder

* `/dataset`: Contains 9 test images of varying sizes used for benchmarking. The dataset is divided into three tiers to evaluate how payload size affects execution time:
  * **Small**: < 500 KB (Tests baseline invocation and network overhead)
  * **Medium**: 1 MB - 3 MB (Simulates standard social media image uploads)
  * **Large**: 5 MB - 10 MB (Tests CPU-intensive processing and memory limits)
