from chainer.functions.activation import lstm
from chainer.functions.array import concat
from chainer.functions.array import split_axis
from chainer import link
from chainer.links.connection import linear
from chainer import variable


class LSTM(link.Chain):

    """Fully-connected LSTM layer.

    This is a fully-connected LSTM layer as a chain. Unlike the
    :func:`~chainer.functions.lstm` function, which is defined as a stateless
    activation function, this chain holds upward and lateral connections as
    child links.

    It also maintains *states*, including the cell state and the output
    at the previous time step. Therefore, it can be used as a *stateful LSTM*.

    Args:
        in_size (int): Dimensionality of input vectors.
        out_size (int): Dimensionality of output vectors.

    Attributes:
        upward (~chainer.links.Linear): Linear layer of upward connections.
        lateral (~chainer.links.Linear): Linear layer of lateral connections.
        c (~chainer.Variable): Cell states of LSTM units.
        h (~chainer.Variable): Output at the previous time step.

    """
    def __init__(self, in_size, out_size):
        super(LSTM, self).__init__(
            upward=linear.Linear(in_size, 4 * out_size),
            lateral=linear.Linear(out_size, 4 * out_size, nobias=True),
        )
        self.state_size = out_size
        self.reset_state()

    def to_cpu(self):
        super(LSTM, self).to_cpu()
        if self.c is not None:
            self.c.to_cpu()
        if self.h is not None:
            self.h.to_cpu()

    def to_gpu(self, device=None):
        super(LSTM, self).to_gpu(device)
        if self.c is not None:
            self.c.to_gpu(device)
        if self.h is not None:
            self.h.to_gpu(device)

    def reset_state(self):
        """Resets the internal state.

        It sets ``None`` to the :attr:`c` and :attr:`h` attributes.

        """
        self.c = self.h = None

    def __call__(self, x):
        """Updates the internal state and returns the LSTM outputs.

        Args:
            x (~chainer.Variable): A new batch from the input sequence.

        Returns:
            ~chainer.Variable: Outputs of updated LSTM units.

        """
        batch = len(x.data)
        lstm_in = self.upward(x)
        h_rest = None
        if self.h is not None:
            if len(self.h.data) > batch:
                h_update, h_rest = split_axis.split_axis(self.h, [batch], axis=0)
                lstm_in += self.lateral(h_update)
            else:
                lstm_in += self.lateral(self.h)
        if self.c is None:
            xp = self.xp
            self.c = variable.Variable(
                xp.zeros((len(x.data), self.state_size), dtype=x.data.dtype),
                volatile='auto')
        self.c, h = lstm.lstm(self.c, lstm_in)
        if h_rest is not None:
            h = concat.concat([h, h_rest], axis=0)
        self.h = h
        return self.h
