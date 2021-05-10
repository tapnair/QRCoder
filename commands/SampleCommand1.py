import adsk.core

from ..apper import apper
from .. import config


class SampleCommand1(apper.Fusion360CommandBase):
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        ao = apper.AppObjects()
        ao.ui.messageBox("Hello Patrick Rainsberry")
