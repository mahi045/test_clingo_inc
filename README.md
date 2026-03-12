# test_clingo_inc
Checking some statistics in Clingo incremental solving

Clingo version:
```
>>> clingo.__version__
'5.8.0'
```

`pacman_base.lp`: the (underlying) logic program
`inputs`: the directory with probabilities in different files (we are solving the pacman_base.lp problem with different probabilities)

We do 10 iterations and each iteration solves the same problem for 32 different probabilities

```
ls inputs
```
You see `instance_1_0.txt` to `instance_9_31.txt`
- `instance_1_0.txt` => first probabilities of iteration 1
- `instance_10_31.txt` => last probabilities of iteration 10


## Run
First clone the repo. Then run `run_clingo_inc.py` in one of the modes (incremental or non-incremental) following the commands given below:


## Run: Non-incremental mode
It grounds the logic program every time for every new probabilities: 
```
python run_clingo_inc.py
```
Output:
```
1-th iteration [Non-incremental]: solving time: 5.0868, choices: 13362.0,  conflict: 29325.0
2-th iteration [Non-incremental]: solving time: 5.7597, choices: 14497.0,  conflict: 32297.0
3-th iteration [Non-incremental]: solving time: 5.5345, choices: 15402.0,  conflict: 34021.0
4-th iteration [Non-incremental]: solving time: 5.1818, choices: 13712.0,  conflict: 31710.0
5-th iteration [Non-incremental]: solving time: 5.5698, choices: 13543.0,  conflict: 30937.0
6-th iteration [Non-incremental]: solving time: 5.0546, choices: 14076.0,  conflict: 32734.0
7-th iteration [Non-incremental]: solving time: 4.9059, choices: 13165.0,  conflict: 31253.0
8-th iteration [Non-incremental]: solving time: 5.0564, choices: 13472.0,  conflict: 32610.0
9-th iteration [Non-incremental]: solving time: 5.6248, choices: 14983.0,  conflict: 35568.0
10-th iteration [Non-incremental]: solving time: 5.5122, choices: 14979.0,  conflict: 34797.0
```

In non-incremental mode, the solving time is more or less similar. 

## Run: Increment mode
It grounds the logic program only once but use the same grounded version for different probabilities:
```
python run_clingo_inc.py 1
```

Output: 
```
1-th iteration [Incremental]: solving time: 4.0702, choices: 8331.0,  conflict: 18504.0
2-th iteration [Incremental]: solving time: 6.3338, choices: 8283.0,  conflict: 18700.0
3-th iteration [Incremental]: solving time: 7.7771, choices: 7662.0,  conflict: 16923.0
4-th iteration [Incremental]: solving time: 6.6829, choices: 5438.0,  conflict: 13473.0
5-th iteration [Incremental]: solving time: 7.0048, choices: 5041.0,  conflict: 13476.0
6-th iteration [Incremental]: solving time: 8.1641, choices: 5710.0,  conflict: 14219.0
7-th iteration [Incremental]: solving time: 8.1261, choices: 5357.0,  conflict: 13990.0
8-th iteration [Incremental]: solving time: 7.5962, choices: 4525.0,  conflict: 12615.0
9-th iteration [Incremental]: solving time: 8.9728, choices: 4767.0,  conflict: 13910.0
10-th iteration [Incremental]: solving time: 10.9387, choices: 6220.0,  conflict: 15759.0
```

Note that the number of choices and conflicts are same for incremental mode, but surprisingly the solving time increases. 

