# Job
A simple tool for recording work time.
All this tool does is record start and stop time stamps in a text file and show
recorded start and stop times to the user.
This is tailored specifically to the authors use case of quickly recording
work time during the day before entering it all into a form in the evening.
Also serves as a log for further analysis.

## Usage
```
python3 job.py <record-file> <option>
```
Options are to record a 'start', 'end' or to 'show' previous work time.
By default 'show' shows the work time of the current day.
To show the work time of the day before use '--yesterday'.
To show the work time of a specific date use '--date'.

All records are kept in a plain text log file, which need to passed as the
first argument.
It's recommended to set up an alias for this, e.g.
```bash
alias j='python3 /path/to/job.py /path/to/records.log'
```
