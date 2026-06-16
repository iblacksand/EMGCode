# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "wfdb>=4.3.1",
# ]
# ///
import wfdb

# load a record using the 'rdrecord' function
record = wfdb.rdrecord("session1_participant13_gesture10_trial1")

# plot the record to screen
wfdb.plot_wfdb(record=record, title="Example signals")
