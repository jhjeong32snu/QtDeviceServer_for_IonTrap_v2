# -*- coding: utf-8 -*-
"""
@author: KMLee
"""

#%%
# Basic Device Characteristics
# Please Don't Change it since it's fixed as model restriction
SynthNV = {
    'num_power' : 1, 'num_freq' : 1, 'num_phase' : 1,
    'min_power' : [-13.49], 'max_power' : [18.55],
    'min_freq' : [34e6], 'max_freq' : [4.5e9],
    'min_phase' : [0], 'max_phase' : [360],
    'type' : 'SynthNV', 'chan' : ['CH 1']}

# CH1 : CH A / CH2 : CH B
SynthHD = {
    'num_power' : 2, 'num_freq' : 2, 'num_phase' : 2,
    'min_power' : [-50,-50], 'max_power' : [20,20],
    'min_freq' : [10e6, 10e6], 'max_freq' : [15e9, 15e9],
    'min_phase' : [0,0], 'max_phase' : [360,360],
    'type' : 'SynthHD', 'chan' : ['CH A', 'CH B']}

APSYN420 = {
    'num_power' : 1, 'num_freq' : 1, 'num_phase' : 1,
    'min_power' : [23], 'max_power' : [23],
    'min_freq' : [10e6], 'max_freq' : [20e9],
    'min_phase' : [0], 'max_phase' : [360],
    'type' : 'APSYN420', 'chan' : ['CH 1']}

# CH1 : BNC / CH2 : NTYPE
SG384 = {
    'num_power' : 2, 'num_freq' : 1, 'num_phase' : 1,
    'min_power' : [-47, -47], 'max_power' : [13, 13], # Power range for SG384 is limited based on BNC output. NTYPE can make -110 to 16.5 dBm signal
    'min_freq' : [950e3], 'max_freq' : [62.5e6],
    'min_phase' : [0], 'max_phase' : [360],
    'type' : 'SG384', 'chan' : ['BNC', 'NTYPE']} # Frequency range for SG384 is limited based on BNC output. NTYPE can generate up to 4GHz signal


#%%
Device_list = {'935SB':SynthHD, 
               '7_4G':SynthHD, 
               '2_1G':SynthHD, 
               'EA_TRAP':SG384, 
               'EC_TRAP':SG384, 
               'EA_MW':APSYN420, 
               'EC_MW':APSYN420}

'''
If you want to change available Frequency/Power range for each device,
Change the value in Device_list
The Shape should be consistant

e.g)
Device_list['935SB']['max_power'] = [15, 15]

ASPYN420 Cannot change power range
'''
Device_list['935SB']['max_power'] = [15, 15]
Device_list['7_4G']['max_power'] = [15, 15]
Device_list['2_1G']['max_power'] = [15, 15]
Device_list['EA_TRAP']['max_power'] = [0, 0]
Device_list['EC_TRAP']['max_power'] = [0, 0]