# Import required modules for sequencer programming
import sys, os
import importlib

from SequencerProgram_v1_07 import SequencerProgram, reg
import SequencerUtility_v1_01 as su
from ArtyS7_v1_02 import ArtyS7
import HardwareDefinition_custom as hd


s = SequencerProgram()

# initialize sequecer
# reset all counters and stopwatches in HardwareDefinition
s.trigger_out([hd.PMT_counter_reset, hd.TRG_counter_reset, hd.PMT_stopwatch_reset, hd.TRG_stopwatch_reset, hd.pulse_trigger_stopwatch_reset, ])

# initialize all registers to zero
for i in range(32):
	s.load_immediate(reg[i], 0)

# instructions programmed by GUI
s.nop()
s.set_output_port(hd.external_control_port, [(hd.EOM_2G_out, 1), ])
s.set_output_port(hd.external_control_port, [(hd.EOM_2G_out, 0), (hd.EOM_7G_1_out, 1), (hd.EOM_7G_2_out, 1), ])
s.set_output_port(hd.external_control_port, [(hd.EOM_7G_1_out, 0), (hd.EOM_7G_2_out, 0), ])
s.set_output_port(hd.external_control_port, [(hd.MW_out, 1), (hd.TEST_out, 1), ])

# turn off counters and stop sequencer
s.set_output_port(hd.counter_control_port, [(hd.PMT_counter_enable, 0), (hd.TRG_counter_enable, 0), ])
s.stop()
# This line will be filled automatically 
# From the Sequencer GUI

