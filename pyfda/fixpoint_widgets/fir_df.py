# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Widget for specifying the parameters of a direct-form DF1 FIR filter
"""
from __future__ import print_function, division, unicode_literals, absolute_import
import sys
import logging
logger = logging.getLogger(__name__)

#import numpy as np
import math
import pyfda.filterbroker as fb

from ..compat import QWidget, QLabel, QVBoxLayout, QHBoxLayout

import pyfda.pyfda_fix_lib as fx
from .fixpoint_helpers import UI_W, UI_W_coeffs, UI_Q, UI_Q_coeffs

import myhdl as hdl
from myhdl import Signal, intbv, always_seq
from pyfda.filter_blocks.support import Samples, Signals

from pyfda.filter_blocks.fda.fir import FilterFIR    

# =============================================================================
# if cmp_version("myhdl", "0.10") >= 0:
#     import myhdl
#     HAS_MYHDL = True
# 
#     fil_blocks_path = os.path.abspath(os.path.join(dirs.INSTALL_DIR, '../../filter-blocks'))
#     if not os.path.exists(fil_blocks_path):
#         logger.error("Invalid path {0}".format(fil_blocks_path))
#     else:
#         if fil_blocks_path not in sys.path:
#             sys.path.append(fil_blocks_path)
#         from pyfda.filter_blocks.fda.fir import FilterFIR
#         from pyfda.filter_blocks.fda.iir import FilterIIR    
# else:
#     HAS_MYHDL = False
# =============================================================================

class FIR_DF(QWidget):
    """
    Widget for entering word formats & quantization
    """
    def __init__(self, parent):
        super(FIR_DF, self).__init__(parent)

        self.title = ("<b>Direct-Form 1 (DF1) FIR Filter</b><br />"
                 "Simple topology.")
        self.img_name = "fir_df.png"

        self._construct_UI()
        self.construct_hdl_filter()

#------------------------------------------------------------------------------

    def _construct_UI(self):
        """
        Intitialize the UI with widgets for coefficient format and input and 
        output quantization
        """
        
        lblHBtnsMsg = QLabel("<b>Fixpoint signal / coeff. formats as WI.WF:</b>", self)
        self.layHBtnsMsg = QHBoxLayout()
        self.layHBtnsMsg.addWidget(lblHBtnsMsg)

        self.wdg_w_input = UI_W(self, label='Input Format <i>Q<sub>X </sub></i>:')
        self.wdg_q_input = UI_Q(self)
        
        self.wdg_w_coeffs = UI_W_coeffs(self, label='Coefficient Format:', enabled=False,
                                        tip_WI='Number of integer bits - edit in the "b,a" tab',
                                        tip_WF='Number of fractional bits - edit in the "b,a" tab',
                                        WI = fb.fil[0]['q_coeff']['WI'],
                                        WF = fb.fil[0]['q_coeff']['WF'])
        self.wdg_q_coeffs = UI_Q_coeffs(self, enabled=False,
                                        cur_ov=fb.fil[0]['q_coeff']['ovfl'], 
                                        cur_q=fb.fil[0]['q_coeff']['quant'])
        self.wdg_w_accu = UI_W(self, label='Accumulator Format <i>Q<sub>A </sub></i>:', WF=30)
        self.wdg_q_accu = UI_Q(self)
        self.wdg_w_output = UI_W(self, label='Output Format <i>Q<sub>Y </sub></i>:')
        self.wdg_q_output = UI_Q(self)
#------------------------------------------------------------------------------

        layVWdg = QVBoxLayout()
        layVWdg.setContentsMargins(0,0,0,0)

        layVWdg.addLayout(self.layHBtnsMsg)

        layVWdg.addWidget(self.wdg_w_input)
        layVWdg.addWidget(self.wdg_q_input)
        
        layVWdg.addWidget(self.wdg_w_coeffs)
        layVWdg.addWidget(self.wdg_q_coeffs)

        layVWdg.addWidget(self.wdg_w_accu)
        layVWdg.addWidget(self.wdg_q_accu)

        layVWdg.addWidget(self.wdg_w_output)
        layVWdg.addWidget(self.wdg_q_output)

        layVWdg.addStretch()

        self.setLayout(layVWdg)
        
#------------------------------------------------------------------------------
    def construct_hdl_filter(self):
        """
        Construct an instance of the HDL filter object
        """
        self.hdlfilter = FilterFIR()     # Standard DF1 filter - hdl_dict should be passed here

#------------------------------------------------------------------------------
    def update_hdl_filter(self):
        """
        Update the HDL filter object with new coefficients, quantization settings etc. when
        
        - it is constructed
        
        - filter design and hence coefficients change
        
        - quantization settings are updated in this widget
        """

        # build the dict with coefficients and fixpoint settings:
        self.hdl_dict = self.get_hdl_dict()
        # setup input and output quantizers
        self.q_i = fx.Fixed(self.hdl_dict['QI']) # setup quantizer for input quantization
        self.q_i.setQobj({'frmt':'dec'})#, 'scale':'int'}) # use integer decimal format
        self.q_o = fx.Fixed(self.hdl_dict['QO']) # setup quantizer for output quantization

        b = [ int(x) for x in self.hdl_dict['QC']['b']] # convert np.int64 to python int

        # call setup method of filter widget - this is not implemented (yet)
        # self.fx_wdg_inst.setup_HDL(self.hdl_dict)
        
        self.hdlfilter.set_coefficients(coeff_b = b)  # Coefficients for the filter

        # pass wordlength for coeffs, input, output
        # TODO: directly pass the hdl_dict here:
        self.hdlfilter.set_word_format(
                (self.hdl_dict['QC']['W'], self.hdl_dict['QC']['WI'], self.hdl_dict['QC']['WF']),
                (self.hdl_dict['QI']['W'], self.hdl_dict['QI']['WI'], self.hdl_dict['QI']['WF']),
                (self.hdl_dict['QO']['W'], self.hdl_dict['QO']['WI'], self.hdl_dict['QO']['WF'])
                )

#------------------------------------------------------------------------------
    def update_UI(self):
        """
        Update all parts of the UI that need to be updated when specs have been
        changed outside this class, e.g. coefficients and coefficient wordlength.

        This is called from one level above by 
        :class:`pyfda.input_widgets.input_fixpoint_specs.Input_Fixpoint_Specs`.
        """
        self.wdg_w_coeffs.load_ui() # update coefficient wordlength
        self.wdg_q_coeffs.load_ui() # update coefficient quantization settings

#==============================================================================
    def get_hdl_dict(self):
        """
        Build the dictionary for passing infos to the fixpoint implementation
        for coefficients, input and output quantization.
        
        Parameters
        ----------
        
        None
        
        Returns
        -------
        hdl_dict : dict

           containing the following keys:

               :'QC': dictionary with coefficients quantization settings
               
               :'QI': dictionary with input quantizer settings
               
               :'QO': dictionary with output quantizer settings
        """
        # quantized coefficients in decimal format
        hdl_dict = {'QC':self.wdg_w_coeffs.c_dict}
        # input quantization parameters
        hdl_dict.update({'QI':{'WI':self.wdg_w_input.WI,
                               'WF':self.wdg_w_input.WF,
                               'W':self.wdg_w_input.W,
                               'ovfl': self.wdg_q_input.ovfl,
                               'quant': self.wdg_q_input.quant
                               }
                        })
        # output quantization parameters
        hdl_dict.update({'QO':{'WI':self.wdg_w_output.WI,
                               'WF':self.wdg_w_output.WF,
                               'W':self.wdg_w_output.W,
                               'ovfl': self.wdg_q_output.ovfl,
                               'quant': self.wdg_q_output.quant
                               }
                        })
    
        return hdl_dict
    
#------------------------------------------------------------------------------    
@hdl.block

def filter_fir(glbl, sigin, sigout, b, coef_w, shared_multiplier=False):
    """Basic FIR direct-form I filter.

    Ports:
        glbl (Global): global signals.
        sigin (Samples): input digital signal.
        sigout (Samples): output digital signal.

    Arguments
    ---------
        b (tuple): numerator coefficents.

    Returns
    --------
        inst (myhdl.Block, list):
    """
    assert isinstance(sigin, Samples)
    assert isinstance(sigout, Samples)
    assert isinstance(b, tuple)
    # All the coefficients need to be an `int`
    rb = [isinstance(bb, int) for bb in b]
    assert all(rb)

    w = sigin.word_format
    w_out = sigout.word_format
    ntaps = len(b)-1
    ymax = 2 ** (w[0]-1)
    sum_abs_b = (sum([abs(x) for x in b]))/2.**(coef_w[0]-1)
    acc_bits = w[0] + coef_w[0] + math.ceil(math.log(sum_abs_b, 2))
    amax = 2**(acc_bits-1)
    qd = acc_bits
    q = acc_bits-w_out[0]

    if q < 0:
        q = 0

    clock, reset = glbl.clock, glbl.reset
    xdv = sigin.valid
    y, ydv = sigout.data, sigout.valid
    x = Signal(intbv(0, min=-ymax, max=ymax))
    # Delay elements, list-of-signals
    ffd = Signals(intbv(0, min=-ymax, max=ymax), ntaps)
    yacc = Signal(intbv(0, min=-amax, max=amax))
    dvd = Signal(bool(0))

    @hdl.always(clock.posedge)
    def beh_direct_form_one():
        if sigin.valid:
            x.next = sigin.data

            for i in range(ntaps-1):
                ffd[i+1].next = ffd[i]

            ffd[0].next = x
            # sum-of-products loop
            c = b[0]
            sop = x * c

            for ii in range(ntaps):
                c = b[ii+1]
                sop = sop + (c * ffd[ii])
            yacc.next = sop

    @always_seq(clock.posedge, reset=reset)
    def beh_output():
        dvd.next = xdv
        y.next = yacc[qd:q].signed()
        ydv.next = dvd

    return beh_direct_form_one, beh_output

#------------------------------------------------------------------------------

if __name__ == '__main__':

    from ..compat import QApplication
    app = QApplication(sys.argv)
    mainw = FIR_DF(None)
    mainw.show()

    app.exec_()
    
    # test using "python -m pyfda.fixpoint_widgets.fir_df1"