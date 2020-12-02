

# Testing Kumiko

Small changes in code often lead to many and unexpected panels to be detected differently.

To have an overview of the consequences of code changes, a testing tool is provided.


# tester.py

Basically switch to `kumiko` top-level directory and run:

`./tester.py`

This will run *Kumiko*, your modified version, on all the comic page templates provided under `./tests/images/`.

But it will also run *Kumiko*'s previous version on the same files and calculate the differences!


# Results

An HTML file is generated under `./tests/results/` that you can open locally (add `--browser firefox` to open it automatically).

It will show you all the differences between the previous git version and yours!

Take a look at the [differences between *Kumiko* v1.0 and v1.1](https://kumiko-demo.njean.me/tests/results/diff-v1.0-v1.1.html).
 
