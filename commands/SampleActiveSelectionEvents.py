import adsk.core

from ..apper import apper
from .. import config


class SampleActiveSelectionEvent(apper.Fusion360ActiveSelectionEvent):

    def selection_event_received(self, event_args, current_selection):
        app = adsk.core.Application.cast(adsk.core.Application.get())
        if len(current_selection) > 0:
            msg = "You have {} items selected. You just selected something of type: {} ".format(
                len(current_selection),
                current_selection[-1].entity.objectType
            )
            app.userInterface.messageBox(msg)

