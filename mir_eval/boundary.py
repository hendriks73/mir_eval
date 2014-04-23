# CREATED:2013-08-13 12:02:42 by Brian McFee <brm2132@columbia.edu>
'''Structural segmentation evaluation, following the protocols of MIREX2012.
    - Boundary detection
        - (precision, recall, f-measure)
        - median distance to nearest boundary
'''

import numpy as np
import functools
import collections

from . import util

def __validate_intervals(intervals):
    '''Internal validation function for interval arrays'''

    # Validate interval shape
    if intervals.ndim != 2 or intervals.shape[1] != 2:
        raise ValueError('Segment intervals should be n-by-2 numpy ndarray')

    # Make sure no times are negative
    if (intervals < 0).any():
        raise ValueError('Negative interval times found')

    # Make sure all intervals have strictly positive duration
    for start, end in intervals:
        if end - start <= 0:
            raise ValueError('Non-positive interval detected: [%.3f, %.3f]' % (start, end))

def validate(metric):
    '''Decorator which checks that the input annotations to a metric
    look like valid segment times, and throws helpful errors if not.

    :parameters:
        - metric : function
            Evaluation metric function.  First two arguments must be
            reference_intervals and estimated_intervals.

    :returns:
        - metric_validated : function
            The function with the segment intervals are validated
    '''
    @functools.wraps(metric)
    def metric_validated(reference_intervals, estimated_intervals, *args, **kwargs):
        '''Validate both reference and estimated intervals'''
        for intervals in [reference_intervals, estimated_intervals]:
            __validate_intervals(intervals)

        return metric(reference_intervals, estimated_intervals, *args, **kwargs)

    return metric_validated

@validate
def detection(reference_intervals, estimated_intervals, window=0.5, beta=1.0, trim=False):
    '''Boundary detection hit-rate.

    A hit is counted whenever an reference boundary is within ``window`` of a estimated
    boundary.  Note that each boundary is matched at most once: this is achieved by computing
    the size of a maximal matching between reference and estimated boundary points, subject
    to the window constraint.

    :usage:
        >>> ref_intervals, ref_labels = mir_eval.io.load_intervals('reference.lab')
        >>> est_intervals, est_labels = mir_eval.io.load_intervals('estimate.lab')
        >>> # With 0.5s windowing
        >>> P05, R05, F05 = mir_eval.boundary.detection(ref_intervals, est_intervals, window=0.5)
        >>> # With 3s windowing
        >>> P3, R3, F3 = mir_eval.boundary.detection(ref_intervals, est_intervals, window=3)
        >>> # Ignoring hits for the beginning and end of track
        >>> P, R, F = mir_eval.boundary.detection(ref_intervals, est_intervals, window=0.5, trim=True)


    :parameters:
        - reference_intervals : np.ndarray, shape=(n, 2)
            reference segment intervals, as returned by `mir_eval.io.load_intervals`

        - estimated_intervals : np.ndarray, shape=(m, 2)
            estimated segment intervals, as returned by `mir_eval.io.load_intervals`

        - window : float > 0
            size of the window of 'correctness' around ground-truth beats (in seconds)

        - beta : float > 0
            weighting constant for F-measure.

        - trim : boolean
            if ``True``, the first and last boundary times are ignored.
            Typically, these denote start (0) and end-markers.

    :returns:
        - precision : float
            precision of estimated predictions

        - recall : float
            recall of reference reference boundaries

        - f_measure : float
            F-measure (weighted harmonic mean of ``precision`` and ``recall``)
    '''

    # Convert intervals to boundaries
    reference_boundaries = util.intervals_to_boundaries(reference_intervals)
    estimated_boundaries = util.intervals_to_boundaries(estimated_intervals)

    # Suppress the first and last intervals
    if trim:
        reference_boundaries = reference_boundaries[1:-1]
        estimated_boundaries = estimated_boundaries[1:-1]

    # If we have no boundaries, we get no score.
    if len(reference_boundaries) == 0 or len(estimated_boundaries) == 0:
        return 0.0, 0.0, 0.0

    matching    = util.match_events(reference_boundaries, 
                                    estimated_boundaries, 
                                    window)
    
    precision   = float(len(matching)) / len(estimated_boundaries)
    recall      = float(len(matching)) / len(reference_boundaries)
    
    f_measure   = util.f_measure(precision, recall, beta=beta)
    
    return precision, recall, f_measure

@validate
def deviation(reference_intervals, estimated_intervals, trim=False):
    '''Compute the median deviations between reference and estimated boundary times.

    :usage:
        >>> ref_intervals, ref_labels = mir_eval.io.load_intervals('reference.lab')
        >>> est_intervals, est_labels = mir_eval.io.load_intervals('estimate.lab')
        >>> r_to_e, e_to_r = mir_eval.boundary.deviation(ref_intervals, est_intervals)

    :parameters:
        - reference_intervals : np.ndarray, shape=(n, 2)
            reference segment intervals, as returned by `mir_eval.io.load_intervals`

        - estimated_intervals : np.ndarray, shape=(m, 2)
            estimated segment intervals, as returned by `mir_eval.io.load_intervals`

        - trim : boolean
            if ``True``, the first and last intervals are ignored.
            Typically, these denote start (0.0) and end-of-track markers.

    :returns:
        - reference_to_estimated : float
            median time from each reference boundary to the closest estimated boundary

        - estimated_to_reference : float
            median time from each estimated boundary to the closest reference boundary
    '''

    # Convert intervals to boundaries
    reference_boundaries = util.intervals_to_boundaries(reference_intervals)
    estimated_boundaries = util.intervals_to_boundaries(estimated_intervals)

    # Suppress the first and last intervals
    if trim:
        reference_boundaries = reference_boundaries[1:-1]
        estimated_boundaries = estimated_boundaries[1:-1]

    # If we have no boundaries, we get no score.
    if len(reference_boundaries) == 0 or len(estimated_boundaries) == 0:
        return np.nan, np.nan

    dist = np.abs( np.subtract.outer(reference_boundaries, estimated_boundaries) )

    estimated_to_reference = np.median(dist.min(axis=0))
    reference_to_estimated = np.median(dist.min(axis=1))

    return reference_to_estimated, estimated_to_reference


# Create an ordered dict mapping metric names to functions
METRICS = collections.OrderedDict()
METRICS['detection'] = detection
METRICS['deviation'] = deviation

