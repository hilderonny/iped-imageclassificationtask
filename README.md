# iped-imageclassificationtask

[IPED](https://github.com/sepinf-inc/IPED) task for image classification via distributed workers. Uses [Task Bridge](https://github.com/hilderonny/taskbridge) together with [ClassifyImage](https://github.com/hilderonny/taskworker-classifyimage) worker for distributing and doing the work.

## Output

Using this task each image file will get the following additional metadata.

|Property|Description|
|-|-|
|`image:classification:classes`|JSON array of the 10 best matching classes. Each entry has a `class`property, a german `name` property and a `probability`.|
|`image:classification:bestclass`|Name fo the best matching class|
|`image:classification:probability`|Probability (0..1) of the best matching class|

## Installation

First download an install [IPED](https://github.com/sepinf-inc/IPED).

Next copy the file `scripts/tasks/ImageClassificationTask.py` into the `scripts/tasks` folder of your IPED installation.

Copy the file `conf/ImageClassification.txt` into the `conf` directory of your IPED installation.

In your IPED folder open the file `IPEDConfig.txt` and add the following line.

```
enableImageClassification = true
```

Finally open the file `conf/TaskInstaller.xml` and look for a line containing `iped.engine.task.ParsingTask`. Add the following line immediately after this line:

```xml
<task script="ImageClassificationTask.py"></task>
```

## Configuration

The configuration is done in the file `conf/ImageClassification.txt` in your IPED directory. This files contains comments on how to setup the connection to the task bridge.
