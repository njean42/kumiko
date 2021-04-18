

# Testing Kumiko

Small changes in code often lead to many and unexpected panels to be detected differently.

To have an overview of the consequences of code changes, a testing tool is provided.


# tester.py

Basically switch to `kumiko` top-level directory and run:

`./tester.py --html`

This will run *Kumiko*, your modified version, on all the comic page templates provided under `./tests/images/`.

But it will also run *Kumiko*'s previous version on the same files and check the differences!


# Results

An HTML file is generated under `./tests/results/` that you can open locally (add `-b firefox` to open it automatically).

It will show you all the differences between the previous git version and yours!

Take a look at the differences between *Kumiko* versions:
* [v1.2.1 and v1.3](https://kumiko.njean.me/tests/results/diff-v1.2.1-v1.3.html)
* [v1.2.1 and v1.2](https://kumiko.njean.me/tests/results/diff-v1.2-v1.2.1.html)
* [v1.2 and v1.1](https://kumiko.njean.me/tests/results/diff-v1.1-v1.2.html)
* [v1.1 and v1.0](https://kumiko.njean.me/tests/results/diff-v1.0-v1.1.html)
