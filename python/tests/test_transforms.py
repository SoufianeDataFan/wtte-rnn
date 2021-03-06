from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import pytest

import numpy as np
import pandas as pd
from six.moves import xrange

from wtte.data_generators import generate_random_df

from wtte.transforms import df_to_padded
from wtte.transforms import padded_to_df
from wtte.transforms import shift_discrete_padded_features
from wtte.transforms import left_pad_to_right_pad
from wtte.transforms import right_pad_to_left_pad
from wtte.transforms import normalize_padded


def df_to_padded_padded_to_df_runner(t_col):
    n_seqs = 5
    max_seq_length = 10
    ids = xrange(n_seqs)
    cols_to_expand = ['event', 'int_column', 'double_column']
    np.random.seed(1)

    df = generate_random_df(n_seqs, max_seq_length)
    df = df.reset_index(drop=True)

    # Column names to transform to tensor
    dtypes = df[cols_to_expand].dtypes.values
    padded = df_to_padded(df, cols_to_expand, 'id', t_col)

    df_new = padded_to_df(padded, cols_to_expand,
                          dtypes, ids, 'id', t_col)
    # Pandas is awful. Index changes when slicing
    df = df[['id', t_col] + cols_to_expand].reset_index(drop=True)
    pd.util.testing.assert_frame_equal(df, df_new)


class TestDfToPaddedPaddedToDf:
    """tests df_to_padded and padded_to_df
    generates a dataframe, transforms it to tensor format then back
    to the same df.
    """

    def test_record_based(self):
        """here only
        """
        df_to_padded_padded_to_df_runner(t_col='t_ix')

    def test_padded_between(self):
        """Tests df_to_padded, padded_to_df
        """
        df_to_padded_padded_to_df_runner(t_col='t_elapsed')


def test_shift_discrete_padded_features():
    """test for `discrete_padded_features`.
        TODO buggy unit. Due to change.
    """
    x = np.array([[[1], [2], [3]]])
    assert x.shape == (1, 3, 1)

    x_shifted = shift_discrete_padded_features(x, fill=0)

    np.testing.assert_array_equal(x_shifted, np.array([[[0], [1], [2]]]))


def test_align_padded():
    """test the function for switching between left-right padd.
    """
    # For simplicity, create a realistic padded tensor
    np.random.seed(1)
    n_seqs = 10
    max_seq_length = 10
    df = generate_random_df(n_seqs, max_seq_length)
    cols_to_expand = ['event', 'int_column', 'double_column']
    padded = df_to_padded(df, cols_to_expand, 'id', 't_elapsed')

    np.testing.assert_array_equal(
        padded, left_pad_to_right_pad(right_pad_to_left_pad(padded)))
    padded = np.copy(np.squeeze(padded))
    np.testing.assert_array_equal(
        padded, left_pad_to_right_pad(right_pad_to_left_pad(padded)))


def test_normalize_padded():
    """
        Assume that a random normal should stay approx unchanged 
        after transformation.
    """
    # No NaNs, zeros, constant cols etc.
    # ONLY NONZERO FALSE
    # [batch,time,feature]
    np.random.seed(1)
    padded = np.random.normal(0, 1, [100000, 10, 2])
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=False)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=False)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # [batch,time]
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=False)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=False)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # ONLY NONZERO TRUE
    # [batch,time,feature]
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # [batch,time]
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # [batch,time,feature] with nans and zeros both settings
    np.random.seed(1)
    padded = np.random.normal(0, 1, [100000, 10, 3])
    # First feature constant 0, should be centered at 0 still.
    padded[:, :, 0] = 0
    # Last 5000 timesteps of first 5 batch masked
    padded[5000:, 5:] = np.nan
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=False)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=False)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # If some timesteps for some batch is zero, this mask should be respected and
    # kept unchanged if only_nonzero
    padded[:100, :5] = 0
    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new2, decimal=2)

    # Binary data
    # With only_nonzero it should leave binary data unchanged
    padded = (np.random.normal(0, 1, [100000, 10, 2]) > 2).astype(float)
    padded[5000:, 5:] = np.nan

    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)

    np.testing.assert_almost_equal(padded_new1, padded_new2, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)

    # Should map scaled binary to [0,1]
    padded_new1, means, stds = normalize_padded(padded * 10, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded * 10, means, stds, only_nonzero=True)

    np.testing.assert_almost_equal(padded_new1, padded_new2, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)

    # If features are numerical (but zero sometimes)
    # we should have same results and mask should be respected.
    padded = (np.random.normal(0, 1, [100000, 10, 1])
              > 0) * np.random.normal(0, 1, [100000, 10, 1])
    padded[np.abs(padded) < 1e-7] = 0

    padded_new1, means, stds = normalize_padded(padded, only_nonzero=True)
    padded_new2, _, _ = normalize_padded(padded, means, stds, only_nonzero=True)

    np.testing.assert_almost_equal(padded_new1, padded_new2, decimal=2)
    np.testing.assert_almost_equal(padded, padded_new1, decimal=2)
