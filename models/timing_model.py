"""
Execution Timing Model.

Uses LSTM to predict entry/exit timing.
"""
from typing import List, Dict, Any, Optional
import torch
import torch.nn as nn
import numpy as np
import logging

logger = logging.getLogger(__name__)


class TimingLSTM(nn.Module):
    """Simple LSTM for timing predictions."""

    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, 2)  # Entry/exit scores

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # Last time step
        out = self.fc(out)
        return torch.sigmoid(out)


class ExecutionTimingModel:
    """LSTM/Transformer-based execution timing model."""

    def __init__(
        self,
        sequence_length: int = 32,
        input_size: int = 6,
        learning_rate: float = 1e-3,
        device: Optional[str] = None
    ):
        """
        Initialize execution timing model.

        Args:
            sequence_length: Number of time steps
            input_size: Number of features per time step
            learning_rate: Learning rate for training
            device: Torch device
        """
        self.sequence_length = sequence_length
        self.input_size = input_size
        self.learning_rate = learning_rate
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = TimingLSTM(input_size=input_size).to(self.device)
        self.criterion = nn.BCELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.is_trained = False

    def prepare_sequence(
        self,
        features: List[Dict[str, float]]
    ) -> torch.Tensor:
        """
        Prepare feature sequence tensor.

        Args:
            features: List of feature dicts

        Returns:
            Tensor of shape (1, seq_len, input_size)
        """
        seq = []
        for feature in features[-self.sequence_length:]:
            seq.append([
                feature.get("frs_score", 0.0),
                feature.get("trust_score", 0.0),
                feature.get("volatility", 0.0),
                feature.get("drift_score", 0.0),
                feature.get("expected_return", 0.0),
                feature.get("momentum", 0.0)
            ])

        # Pad if shorter
        while len(seq) < self.sequence_length:
            seq.insert(0, [0.0] * self.input_size)

        seq_tensor = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
        return seq_tensor.to(self.device)

    def train_on_batch(
        self,
        batch_features: List[List[Dict[str, float]]],
        batch_labels: List[List[int]]
    ) -> float:
        """
        Train on batch of sequences.

        Args:
            batch_features: List of feature sequences
            batch_labels: List of [entry_label, exit_label]

        Returns:
            Training loss
        """
        self.model.train()
        losses = []

        for features, labels in zip(batch_features, batch_labels):
            inputs = self.prepare_sequence(features)
            targets = torch.tensor(labels, dtype=torch.float32).unsqueeze(0).to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            losses.append(loss.item())

        if losses:
            avg_loss = float(np.mean(losses))
            self.is_trained = True
            return avg_loss
        return 0.0

    def predict_timing(
        self,
        recent_features: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Predict entry/exit timing probabilities.

        Args:
            recent_features: Recent feature sequence

        Returns:
            Dict with entry/exit probabilities
        """
        self.model.eval()
        with torch.no_grad():
            inputs = self.prepare_sequence(recent_features)
            outputs = self.model(inputs)
            entry_prob, exit_prob = outputs[0].tolist()

        # Interpret results
        entry_signal = entry_prob >= 0.65
        exit_signal = exit_prob >= 0.65

        return {
            "entry_probability": float(entry_prob),
            "exit_probability": float(exit_prob),
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "model_trained": self.is_trained,
            "recommendation": self._get_recommendation(entry_prob, exit_prob)
        }

    @staticmethod
    def _get_recommendation(entry_prob: float, exit_prob: float) -> str:
        """Get recommendation based on probabilities."""
        if entry_prob >= 0.7 and exit_prob < 0.4:
            return "ENTER_POSITION"
        elif exit_prob >= 0.7:
            return "EXIT_POSITION"
        elif entry_prob >= 0.6:
            return "PREPARE_TO_ENTER"
        elif exit_prob >= 0.6:
            return "PREPARE_TO_EXIT"
        else:
            return "HOLD"











