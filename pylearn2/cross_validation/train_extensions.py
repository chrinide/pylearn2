"""
Cross-validation training extensions.
"""
from copy import deepcopy
import numpy as np

from pylearn2.train import SerializationGuard
from pylearn2.train_extensions import TrainExtension
from pylearn2.utils import serial


class TrainCVExtension(object):
    """
    TrainCV extension class. This class operates on the Train objects
    corresponding to each fold of cross-validation, and therefore does not
    implement an on_monitor method.
    """
    def setup(self, trainers):
        """
        Set up training extension.

        Parameters
        ----------
        trainers : list
            List of Train objects belonging to the parent TrainCV object.
        """

    def on_save(self, trainers):
        """
        Called by TrainCV just before saving models.

        Parameters
        ----------
        trainers : list
            List of Train objects belonging to the parent TrainCV object.
        """


class MonitorBasedSaveBestCV(TrainCVExtension):
    """
    Save best model for each cross-validation fold. Based on
    train_extensions.best_params.MonitorBasedSaveBest.

    Parameters
    ----------
    channel_name : str
        Channel to monitor.
    save_path : str
        Output filename.
    higher_is_better : bool
        Whether a higher channel value indicates a better model.
    """
    def __init__(self, channel_name, save_path, higher_is_better=False):
        self.channel_name = channel_name
        self.save_path = save_path
        self.higher_is_better = higher_is_better
        self.best_cost = np.inf
        self.best_model = None

    def setup(self, trainers):
        """
        Add tracking to all trainers.

        Parameters
        ----------
        trainers : list
            List of Train objects belonging to the parent TrainCV object.
        """
        for trainer in trainers:
            extension = MonitorBasedStoreBest(self.channel_name,
                                              self.higher_is_better)
            trainer.extensions.append(extension)

    def on_save(self, trainers):
        """
        Save best model from each cross-validation fold.

        Parameters
        ----------
        trainers : list
            List of Train objects belonging to the parent TrainCV object.
        """
        models = []
        for trainer in trainers:
            for extension in trainer.extensions:
                if isinstance(extension, MonitorBasedStoreBest):
                    models.append(extension.best_model)
                    break
        assert len(models) == len(trainers)
        try:
            for trainer in trainers:
                trainer.dataset._serialization_guard = SerializationGuard()
                serial.save(self.save_path, models, on_overwrite='backup')
        finally:
            for trainer in trainers:
                trainer.dataset._serialization_guard = None


class MonitorBasedStoreBest(TrainExtension):
    """
    Save best model for each cross-validation fold. Based on
    train_extensions.best_params.MonitorBasedSaveBest.

    Parameters
    ----------
    channel_name : str
        Channel to monitor.
    save_path : str
        Output filename.
    higher_is_better : bool
        Whether a higher channel value indicates a better model.
    """
    def __init__(self, channel_name, higher_is_better=False):
        self.channel_name = channel_name
        self.higher_is_better = higher_is_better
        self.best_cost = np.inf
        self.best_model = None

    def on_monitor(self, model, dataset, algorithm):
        """
        Check if the model performs better than before. Save best models in
        memory to avoid race conditions.

        Parameters
        ----------
        model : Model
            Model to monitor.
        dataset : Dataset
            Training dataset.
        algorithm : TrainingAlgorithm
            Training algorithm.
        """
        monitor = model.monitor
        channels = monitor.channels
        channel = channels[self.channel_name]
        val_record = channel.val_record
        if self.higher_is_better:
            new_cost = -1 * val_record[-1]
        else:
            new_cost = val_record[-1]

        if new_cost < self.best_cost:
            self.best_cost = new_cost
            self.best_model = deepcopy(model)
