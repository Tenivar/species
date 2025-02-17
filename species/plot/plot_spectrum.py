"""
Module with a function for plotting a spectral energy distribution
that includes photometric and/or spectral data and/or models.
"""

import math
import warnings

from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from typeguard import typechecked
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter

from species.core.box import (
    ModelBox,
    ObjectBox,
    PhotometryBox,
    ResidualsBox,
    SpectrumBox,
    SynphotBox,
)
from species.read.read_filter import ReadFilter
from species.util.core_util import print_section
from species.util.plot_util import create_model_label


@typechecked
def plot_spectrum(
    boxes: list,
    filters: Optional[List[str]] = None,
    residuals: Optional[ResidualsBox] = None,
    plot_kwargs: Optional[List[Optional[dict]]] = None,
    envelope: bool = False,
    xlim: Optional[Tuple[float, float]] = None,
    ylim: Optional[Tuple[float, float]] = None,
    ylim_res: Optional[Tuple[float, float]] = None,
    scale: Optional[Tuple[str, str]] = None,
    title: Optional[str] = None,
    offset: Optional[Tuple[float, float]] = None,
    legend: Optional[
        Union[
            str,
            dict,
            Tuple[float, float],
            List[Optional[Union[dict, str, Tuple[float, float]]]],
        ]
    ] = None,
    figsize: Optional[Tuple[float, float]] = (6.0, 3.0),
    object_type: str = "planet",
    quantity: str = "flux density",
    output: Optional[str] = None,
    leg_param: Optional[List[str]] = None,
    param_fmt: Optional[Dict[str, str]] = None,
    grid_hspace: float = 0.1,
    inc_model_name: bool = False,
    units: Tuple[str, str] = ("um", "W m-2 um-1"),
) -> mpl.figure.Figure:
    """
    Function for plotting a spectral energy distribution and combining
    various data such as spectra, photometric fluxes, model spectra,
    synthetic photometry, fit residuals, and filter profiles.

    Parameters
    ----------
    boxes : list(species.core.box)
        Boxes with data that will be included in the plot.
    filters : list(str), None
        Filter names for which the transmission profile is plotted.
        Not plotted if set to ``None``.
    residuals : species.core.box.ResidualsBox, None
        Box with residuals of a fit. Not plotted if set to ``None``.
    plot_kwargs : list(dict), None
        List with dictionaries of keyword arguments for each box.
        For example, if the ``boxes`` are a ``ModelBox`` and
        ``ObjectBox``:

        .. code-block:: python

            plot_kwargs=[{'ls': '-', 'lw': 1., 'color': 'black'},
                         {'spectrum_1': {'marker': 'o', 'ms': 3., 'color': 'tab:brown', 'ls': 'none'},
                          'spectrum_2': {'marker': 'o', 'ms': 3., 'color': 'tab:blue', 'ls': 'none'},
                          'Paranal/SPHERE.IRDIS_D_H23_3': {'marker': 's', 'ms': 4., 'color': 'tab:cyan', 'ls': 'none'},
                          'Paranal/SPHERE.IRDIS_D_K12_1': [{'marker': 's', 'ms': 4., 'color': 'tab:orange', 'ls': 'none'},
                                                           {'marker': 's', 'ms': 4., 'color': 'tab:red', 'ls': 'none'}],
                          'Paranal/NACO.Lp': {'marker': 's', 'ms': 4., 'color': 'tab:green', 'ls': 'none'},
                          'Paranal/NACO.Mp': {'marker': 's', 'ms': 4., 'color': 'tab:green', 'ls': 'none'}}]

        For an ``ObjectBox``, the dictionary contains items for the
        different spectrum and filter names stored with
        :func:`~species.data.database.Database.add_object`. In case
        both and ``ObjectBox`` and a ``SynphotBox`` are provided,
        then the latter can be set to ``None`` in order to use the
        same (but open) symbols as the data from the ``ObjectBox``.
        Note that if a filter name is duplicated in an ``ObjectBox``
        (Paranal/SPHERE.IRDIS_D_K12_1 in the example) then a list
        with two dictionaries should be provided. Colors are
        automatically chosen if ``plot_kwargs`` is set to ``None``.
    envelope : bool
        Plot an envelope instead of the individual samples in case
        the list of ``boxes`` contains a list with
        :class:`~species.core.box.ModelBox` objects from
        :func:`~species.data.database.Database.get_mcmc_spectra`
        or :func:`~species.data.database.Database.get_retrieval_spectra`.
        The envelopes show the 68 and 99.7 percent confidence intervals,
        so :math:`1\\sigma` and :math:`3\\sigma` in case of Gaussian
        distributions.
    xlim : tuple(float, float)
        Limits of the wavelength axis.
    ylim : tuple(float, float)
        Limits of the flux axis.
    ylim_res : tuple(float, float), None
        Limits of the residuals axis. Automatically chosen
        (based on the minimum and maximum residual value)
        if set to ``None``.
    scale : tuple(str, str), None
        Scale of the x and y axes ('linear' or 'log').
        The scale is set to ``('linear', 'linear')`` if
        set to ``None``.
    title : str
        Title.
    offset : tuple(float, float)
        Offset for the label of the x- and y-axis.
    legend : str, tuple, dict, list(dict, dict), None
        Location of the legend (str or tuple(float, float))
        or a dictionary with the ``**kwargs`` of
        ``matplotlib.pyplot.legend``, for example
        ``{'loc': 'upper left', 'fontsize: 12.}``. Alternatively,
        a list with two values can be provided to separate the
        model and data handles in two legends. Each of these two
        elements can be set to ``None``. For example,
        ``[None, {'loc': 'upper left', 'fontsize: 12.}]``, if
        only the data points should be included in a legend.
    figsize : tuple(float, float)
        Figure size.
    object_type : str
        Object type ('planet' or 'star'). With 'planet', the radius
        and mass are expressed in Jupiter units. With 'star', the
        radius and mass are expressed in solar units.
    quantity: str
        The quantity of the y-axis ('flux density', 'flux',
        or 'magnitude').
    output : str, None
        Output filename for the plot. The plot is shown in an
        interface window if the argument is set to ``None``.
    leg_param : list(str), None
        List with the parameters to include in the legend of the
        model spectra. Apart from atmospheric parameters (e.g.
        'teff', 'logg', 'radius') also parameters such as 'mass'
        and 'luminosity' can be included. The default atmospheric
        parameters are included in the legend if the argument is
        set to ``None``.
    param_fmt : dict(str, str), None
        Dictionary with formats that will be used for the model
        parameter. The parameters are included in the ``legend``
        when plotting the model spectra. Default formats are
        used if the argument of ``param_fmt`` is set to ``None``.
        Formats should provided for example as '.2f' for two
        decimals, '.0f' for zero decimals, and '.1e' for
        exponential notation with one decimal.
    grid_hspace : float
        The relative height spacing between subplots, expressed
        as a fraction of the average axis height. The default
        value is set to 0.1.
    inc_model_name : bool
        Include the model name in the legend of any
        :class:`~species.core.box.ModelBox`.
    units : tuple(str, str)
        This parameter has not yet been implemented.

    Returns
    -------
    matplotlib.figure.Figure
        The ``Figure`` object that can be used for further
        customization of the plot.
    """

    print_section("Plot spectrum")

    print("Boxes:")
    for item in boxes:
        if isinstance(item, list):
            item_type = item[0].__class__.__name__
            print(f"   - List with {len(item)} x {item_type}")
        else:
            print(f"   - {item.__class__.__name__}")

    print(f"\nObject type: {object_type}")
    print(f"Quantity: {quantity}")
    print(f"Filter profiles: {filters}")

    print(f"\nFigure size: {figsize}")
    print(f"Legend parameters: {leg_param}")
    print(f"Include model name: {inc_model_name}")

    plt.rcParams["font.family"] = "serif"
    plt.rcParams["mathtext.fontset"] = "dejavuserif"
    plt.rcParams["axes.axisbelow"] = False

    if plot_kwargs is None:
        plot_kwargs = []

    elif plot_kwargs is not None and len(boxes) != len(plot_kwargs):
        raise ValueError(
            f"The number of 'boxes' ({len(boxes)}) should be equal to the "
            f"number of items in 'plot_kwargs' ({len(plot_kwargs)})."
        )

    if leg_param is None:
        leg_param = []

    if param_fmt is None:
        param_fmt = {}

    # Add missing parameter formats

    param_add = ["teff", "disk_teff", "disk_radius"]

    for param_item in param_add:
        if param_item not in param_fmt:
            param_fmt[param_item] = ".0f"

    param_add = [
        "radius",
        "logg",
        "feh",
        "metallicity",
        "fsed",
        "distance",
        "parallax",
        "mass",
        "ism_ext",
        "lognorm_ext",
        "powerlaw_ext",
        "log_flux_scaling",
    ]

    for param_item in param_add:
        if param_item not in param_fmt:
            param_fmt[param_item] = ".1f"

    param_add = ["co", "c_o_ratio", "ad_index", "luminosity"]

    for param_item in param_add:
        if param_item not in param_fmt:
            param_fmt[param_item] = ".2f"

    param_add = ["flux_scaling", "flux_offset"]

    for param_item in param_add:
        if param_item not in param_fmt:
            param_fmt[param_item] = ".2e"

    if residuals is not None and filters is not None:
        fig = plt.figure(figsize=figsize)
        grid_sp = mpl.gridspec.GridSpec(3, 1, height_ratios=[1, 3, 1])
        grid_sp.update(wspace=0, hspace=grid_hspace, left=0, right=1, bottom=0, top=1)

        ax1 = plt.subplot(grid_sp[1, 0])
        ax2 = plt.subplot(grid_sp[0, 0])
        ax3 = plt.subplot(grid_sp[2, 0])

    elif residuals is not None:
        fig = plt.figure(figsize=figsize)
        grid_sp = mpl.gridspec.GridSpec(2, 1, height_ratios=[4, 1])
        grid_sp.update(wspace=0, hspace=grid_hspace, left=0, right=1, bottom=0, top=1)

        ax1 = plt.subplot(grid_sp[0, 0])
        ax2 = None
        ax3 = plt.subplot(grid_sp[1, 0])

    elif filters is not None:
        fig = plt.figure(figsize=figsize)
        grid_sp = mpl.gridspec.GridSpec(2, 1, height_ratios=[1, 4])
        grid_sp.update(wspace=0, hspace=grid_hspace, left=0, right=1, bottom=0, top=1)

        ax1 = plt.subplot(grid_sp[1, 0])
        ax2 = plt.subplot(grid_sp[0, 0])
        ax3 = None

    else:
        fig = plt.figure(figsize=figsize)
        grid_sp = mpl.gridspec.GridSpec(1, 1)
        grid_sp.update(wspace=0, hspace=grid_hspace, left=0, right=1, bottom=0, top=1)

        ax1 = plt.subplot(grid_sp[0, 0])
        ax2 = None
        ax3 = None

    if residuals is not None:
        labelbottom = False
    else:
        labelbottom = True

    if scale is None:
        scale = ("linear", "linear")

    ax1.set_xscale(scale[0])
    ax1.set_yscale(scale[1])

    if filters is not None:
        ax2.set_xscale(scale[0])

    if residuals is not None:
        ax3.set_xscale(scale[0])

    ax1.tick_params(
        axis="both",
        which="major",
        colors="black",
        labelcolor="black",
        direction="in",
        width=1,
        length=5,
        labelsize=12,
        top=True,
        bottom=True,
        left=True,
        right=True,
        labelbottom=labelbottom,
    )

    ax1.tick_params(
        axis="both",
        which="minor",
        colors="black",
        labelcolor="black",
        direction="in",
        width=1,
        length=3,
        labelsize=12,
        top=True,
        bottom=True,
        left=True,
        right=True,
        labelbottom=labelbottom,
    )

    if filters is not None:
        ax2.tick_params(
            axis="both",
            which="major",
            colors="black",
            labelcolor="black",
            direction="in",
            width=1,
            length=5,
            labelsize=12,
            top=True,
            bottom=True,
            left=True,
            right=True,
            labelbottom=False,
        )

        ax2.tick_params(
            axis="both",
            which="minor",
            colors="black",
            labelcolor="black",
            direction="in",
            width=1,
            length=3,
            labelsize=12,
            top=True,
            bottom=True,
            left=True,
            right=True,
            labelbottom=False,
        )

    if residuals is not None:
        ax3.tick_params(
            axis="both",
            which="major",
            colors="black",
            labelcolor="black",
            direction="in",
            width=1,
            length=5,
            labelsize=12,
            top=True,
            bottom=True,
            left=True,
            right=True,
        )

        ax3.tick_params(
            axis="both",
            which="minor",
            colors="black",
            labelcolor="black",
            direction="in",
            width=1,
            length=3,
            labelsize=12,
            top=True,
            bottom=True,
            left=True,
            right=True,
        )

    if scale[0] == "linear":
        ax1.xaxis.set_minor_locator(AutoMinorLocator(5))

    if scale[1] == "linear":
        ax1.yaxis.set_minor_locator(AutoMinorLocator(5))

    # ax1.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e0])
    # ax3.set_yticks([-2., 0., 2.])

    if filters is not None:
        if scale[0] == "linear":
            ax2.xaxis.set_minor_locator(AutoMinorLocator(5))

    if residuals is not None:
        if scale[0] == "linear":
            ax3.xaxis.set_minor_locator(AutoMinorLocator(5))

    if residuals is not None and filters is not None:
        ax1.set_xlabel("")
        ax2.set_xlabel("")
        ax3.set_xlabel("Wavelength (\N{GREEK SMALL LETTER MU}m)", fontsize=13)

    elif residuals is not None:
        ax1.set_xlabel("")
        ax3.set_xlabel("Wavelength (\N{GREEK SMALL LETTER MU}m)", fontsize=11)

    elif filters is not None:
        ax1.set_xlabel("Wavelength (\N{GREEK SMALL LETTER MU}m)", fontsize=13)
        ax2.set_xlabel("")

    else:
        ax1.set_xlabel("Wavelength (\N{GREEK SMALL LETTER MU}m)", fontsize=13)

    if filters is not None:
        ax2.set_ylabel(r"$T_\lambda$", fontsize=13)

    if residuals is not None:
        if quantity == "flux density":
            ax3.set_ylabel(r"$\Delta$$F_\lambda$ ($\sigma$)", fontsize=11)

        elif quantity == "flux":
            ax3.set_ylabel(r"$\Delta$$F_\lambda$ ($\sigma$)", fontsize=11)

    if xlim is None:
        ax1.set_xlim(0.5, 5.0)
    else:
        ax1.set_xlim(xlim[0], xlim[1])

    if quantity == "magnitude":
        scaling = 1.0
        ax1.set_ylabel("Contrast (mag)", fontsize=13)

        if ylim:
            ax1.set_ylim(ylim[0], ylim[1])

    else:
        if ylim:
            ax1.set_ylim(ylim[0], ylim[1])

            ylim = ax1.get_ylim()

            if scale[1] == "linear":
                exponent = math.floor(math.log10(ylim[1]))
                scaling = 10.0**exponent

            else:
                exponent = None
                scaling = 1.0

            if quantity == "flux density":
                if exponent is None:
                    ylabel = (
                        r"$F_\lambda$ (W m$^{-2}$ "
                        + "\N{GREEK SMALL LETTER MU}m$^{-1}$)"
                    )

                else:
                    ylabel = (
                        r"$F_\lambda$ (10$^{"
                        + str(exponent)
                        + r"}$"
                        + " W m$^{-2}$ \N{GREEK SMALL LETTER MU}m$^{-1}$)"
                    )

            elif quantity == "flux":
                if exponent is None:
                    ylabel = r"$\lambda$$F_\lambda$ (W m$^{-2}$)"

                else:
                    ylabel = (
                        r"$\lambda$$F_\lambda$ (10$^{"
                        + str(exponent)
                        + r"}$ W m$^{-2}$)"
                    )

            ax1.set_ylabel(ylabel, fontsize=11)
            ax1.set_ylim(ylim[0] / scaling, ylim[1] / scaling)

            if ylim[0] < 0.0:
                ax1.axhline(
                    0.0, ls="--", lw=0.7, color="gray", dashes=(2, 4), zorder=0.5
                )

        else:
            if quantity == "flux density":
                ax1.set_ylabel(
                    r"$F_\lambda$" + " (W m$^{-2}$ \N{GREEK SMALL LETTER MU}m$^{-1}$)",
                    fontsize=11,
                )

            elif quantity == "flux":
                ax1.set_ylabel(r"$\lambda$$F_\lambda$ (W m$^{-2}$)", fontsize=11)

            scaling = 1.0

    xlim = ax1.get_xlim()

    if filters is not None:
        ax2.set_xlim(xlim[0], xlim[1])
        ax2.set_ylim(0.0, 1.0)

    if residuals is not None:
        ax3.set_xlim(xlim[0], xlim[1])

    if offset is not None and residuals is not None and filters is not None:
        ax3.get_xaxis().set_label_coords(0.5, offset[0])

        ax1.get_yaxis().set_label_coords(offset[1], 0.5)
        ax2.get_yaxis().set_label_coords(offset[1], 0.5)
        ax3.get_yaxis().set_label_coords(offset[1], 0.5)

    elif offset is not None and filters is not None:
        ax1.get_xaxis().set_label_coords(0.5, offset[0])

        ax1.get_yaxis().set_label_coords(offset[1], 0.5)
        ax2.get_yaxis().set_label_coords(offset[1], 0.5)

    elif offset is not None and residuals is not None:
        ax3.get_xaxis().set_label_coords(0.5, offset[0])

        ax1.get_yaxis().set_label_coords(offset[1], 0.5)
        ax3.get_yaxis().set_label_coords(offset[1], 0.5)

    elif offset is not None:
        ax1.get_xaxis().set_label_coords(0.5, offset[0])
        ax1.get_yaxis().set_label_coords(offset[1], 0.5)

    # else:
    #     ax1.get_xaxis().set_label_coords(0.5, -0.12)
    #     ax1.get_yaxis().set_label_coords(-0.1, 0.5)

    for j, box_item in enumerate(boxes):
        flux_scaling = 1.0

        if j < len(boxes):
            plot_kwargs.append(None)

        if isinstance(box_item, (SpectrumBox, ModelBox)):
            wavelength = box_item.wavelength
            flux = box_item.flux

            if isinstance(wavelength[0], (np.float32, np.float64)):
                data = np.array(flux, dtype=np.float64)
                masked = np.ma.array(data, mask=np.isnan(data))

                if isinstance(box_item, ModelBox):
                    param = box_item.parameters.copy()

                    label = create_model_label(
                        model_param=param,
                        object_type=object_type,
                        model_name=box_item.model,
                        inc_model_name=inc_model_name,
                        leg_param=leg_param,
                        param_fmt=param_fmt,
                    )

                else:
                    label = None

                if plot_kwargs[j]:
                    kwargs_copy = plot_kwargs[j].copy()

                    if "label" in kwargs_copy:
                        if kwargs_copy["label"] is None:
                            label = None
                        else:
                            label = kwargs_copy["label"]

                        del kwargs_copy["label"]

                    if quantity == "flux":
                        flux_scaling = wavelength

                    if "zorder" not in kwargs_copy:
                        kwargs_copy["zorder"] = 2.0

                    ax1.plot(
                        wavelength,
                        flux_scaling * masked / scaling,
                        label=label,
                        **kwargs_copy,
                    )

                else:
                    if quantity == "flux":
                        flux_scaling = wavelength

                    ax1.plot(
                        wavelength,
                        flux_scaling * masked / scaling,
                        lw=0.5,
                        label=label,
                        zorder=2,
                    )

            elif isinstance(wavelength[0], (np.ndarray)):
                for i, item in enumerate(wavelength):
                    data = np.array(flux[i], dtype=np.float64)
                    masked = np.ma.array(data, mask=np.isnan(data))

                    if isinstance(box_item.name[i], bytes):
                        label = box_item.name[i].decode("utf-8")
                    else:
                        label = box_item.name[i]

                    if quantity == "flux":
                        flux_scaling = item

                    ax1.plot(item, flux_scaling * masked / scaling, lw=0.5, label=label)

        elif isinstance(box_item, list):
            if envelope:
                spec_list = np.zeros((len(box_item), box_item[0].flux.size))
            else:
                spec_list = None

            for i, item in enumerate(box_item):
                wavelength = item.wavelength
                flux = item.flux

                # data = np.array(flux, dtype=np.float64)
                data = flux.astype(np.float64)
                masked = np.ma.array(data, mask=np.isnan(data))

                if quantity == "flux":
                    flux_scaling = wavelength

                if envelope:
                    spec_list[i] = flux

                else:
                    if plot_kwargs[j]:
                        if "zorder" not in plot_kwargs[j]:
                            plot_kwargs[j]["zorder"] = 1.0

                        ax1.plot(
                            wavelength,
                            flux_scaling * masked / scaling,
                            **plot_kwargs[j],
                        )
                    else:
                        ax1.plot(
                            wavelength,
                            flux_scaling * masked / scaling,
                            color="gray",
                            lw=0.2,
                            alpha=0.5,
                            zorder=1,
                        )

            if envelope:
                spec_percent = np.percentile(spec_list, [0.3, 16.0, 84.0, 99.7], axis=0)

                if plot_kwargs[j]:
                    if "zorder" not in plot_kwargs[j]:
                        plot_kwargs[j]["zorder"] = 1.0

                    if "alpha" in plot_kwargs[j]:
                        del plot_kwargs[j]["alpha"]

                    ax1.fill_between(
                        x=wavelength,
                        y1=flux_scaling * spec_percent[0] / scaling,
                        y2=flux_scaling * spec_percent[3] / scaling,
                        alpha=0.4,
                        **plot_kwargs[j],
                    )

                    ax1.fill_between(
                        x=wavelength,
                        y1=flux_scaling * spec_percent[1] / scaling,
                        y2=flux_scaling * spec_percent[2] / scaling,
                        alpha=1.0,
                        **plot_kwargs[j],
                    )

                else:
                    ax1.fill_between(
                        x=wavelength,
                        y1=flux_scaling * spec_percent[0] / scaling,
                        y2=flux_scaling * spec_percent[3] / scaling,
                        color="peachpuff",
                        alpha=0.4,
                        zorder=1,
                        linewidth=0.0,
                    )

                    ax1.fill_between(
                        x=wavelength,
                        y1=flux_scaling * spec_percent[1] / scaling,
                        y2=flux_scaling * spec_percent[2] / scaling,
                        color="peachpuff",
                        alpha=1.0,
                        zorder=1,
                        linewidth=0.0,
                    )

        elif isinstance(box_item, PhotometryBox):
            label_check = []

            for i, item in enumerate(box_item.wavelength):
                transmission = ReadFilter(box_item.filter_name[i])
                fwhm = transmission.filter_fwhm()

                if quantity == "flux":
                    flux_scaling = item

                if plot_kwargs[j]:
                    if (
                        "label" in plot_kwargs[j]
                        and plot_kwargs[j]["label"] not in label_check
                    ):
                        label_check.append(plot_kwargs[j]["label"])

                    elif (
                        "label" in plot_kwargs[j]
                        and plot_kwargs[j]["label"] in label_check
                    ):
                        del plot_kwargs[j]["label"]

                    if box_item.flux[i][1] is None:
                        if "zorder" not in plot_kwargs[j]:
                            plot_kwargs[j]["zorder"] = 3.0

                        ax1.errorbar(
                            item,
                            flux_scaling * box_item.flux[i][0] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=None,
                            **plot_kwargs[j],
                        )

                    else:
                        if "zorder" not in plot_kwargs[j]:
                            plot_kwargs[j]["zorder"] = 3.0

                        ax1.errorbar(
                            item,
                            flux_scaling * box_item.flux[i][0] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=flux_scaling * box_item.flux[i][1] / scaling,
                            **plot_kwargs[j],
                        )

                else:
                    if box_item.flux[i][1] is None:
                        ax1.errorbar(
                            item,
                            flux_scaling * box_item.flux[i][0] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=None,
                            marker="s",
                            ms=6,
                            color="black",
                            zorder=3,
                        )

                    else:
                        ax1.errorbar(
                            item,
                            flux_scaling * box_item.flux[i][0] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=flux_scaling * box_item.flux[i][1] / scaling,
                            marker="s",
                            ms=6,
                            color="black",
                            zorder=3,
                        )

        elif isinstance(box_item, ObjectBox):
            if box_item.spectrum is not None:
                spec_list = []
                wavel_list = []

                for item in box_item.spectrum:
                    spec_list.append(item)
                    wavel_list.append(box_item.spectrum[item][0][0, 0])

                sort_index = np.argsort(wavel_list)
                spec_sort = []

                for i in range(sort_index.size):
                    spec_sort.append(spec_list[sort_index[i]])

                for key in spec_sort:
                    masked = np.ma.array(
                        box_item.spectrum[key][0],
                        mask=np.isnan(box_item.spectrum[key][0]),
                    )

                    if quantity == "flux":
                        flux_scaling = masked[:, 0]

                    if not plot_kwargs[j] or key not in plot_kwargs[j]:
                        plot_obj = ax1.errorbar(
                            masked[:, 0],
                            flux_scaling * masked[:, 1] / scaling,
                            yerr=flux_scaling * masked[:, 2] / scaling,
                            ms=2,
                            marker="s",
                            zorder=2.5,
                            ls="none",
                        )

                        if plot_kwargs[j] is None:
                            plot_kwargs[j] = {}

                        plot_kwargs[j][key] = {
                            "marker": "s",
                            "ms": 2.0,
                            "ls": "none",
                            "color": plot_obj[0].get_color(),
                        }

                    elif "marker" not in plot_kwargs[j][key]:
                        # Plot the spectrum as a line without error bars
                        # (e.g. when the spectrum has a high spectral resolution)
                        plot_obj = ax1.plot(
                            masked[:, 0],
                            flux_scaling * masked[:, 1] / scaling,
                            **plot_kwargs[j][key],
                        )

                    else:
                        if "zorder" not in plot_kwargs[j][key]:
                            plot_kwargs[j][key]["zorder"] = 2.5

                        ax1.errorbar(
                            masked[:, 0],
                            flux_scaling * masked[:, 1] / scaling,
                            yerr=flux_scaling * masked[:, 2] / scaling,
                            **plot_kwargs[j][key],
                        )

            if box_item.flux is not None:
                filter_list = []
                wavel_list = []

                for item in box_item.flux:
                    read_filt = ReadFilter(item)
                    filter_list.append(item)
                    wavel_list.append(read_filt.mean_wavelength())

                sort_index = np.argsort(wavel_list)
                filter_sort = []

                for i in range(sort_index.size):
                    filter_sort.append(filter_list[sort_index[i]])

                for item in filter_sort:
                    transmission = ReadFilter(item)
                    wavelength = transmission.mean_wavelength()
                    fwhm = transmission.filter_fwhm()

                    if not plot_kwargs[j] or item not in plot_kwargs[j]:
                        if not plot_kwargs[j]:
                            plot_kwargs[j] = {}

                        if quantity == "flux":
                            flux_scaling = wavelength

                        scale_tmp = flux_scaling / scaling

                        if isinstance(box_item.flux[item][0], np.ndarray):
                            for i in range(box_item.flux[item].shape[1]):
                                plot_obj = ax1.errorbar(
                                    wavelength,
                                    scale_tmp * box_item.flux[item][0, i],
                                    xerr=fwhm / 2.0,
                                    yerr=scale_tmp * box_item.flux[item][1, i],
                                    marker="s",
                                    ms=5,
                                    zorder=3,
                                    color="black",
                                )

                        else:
                            plot_obj = ax1.errorbar(
                                wavelength,
                                scale_tmp * box_item.flux[item][0],
                                xerr=fwhm / 2.0,
                                yerr=scale_tmp * box_item.flux[item][1],
                                marker="s",
                                ms=5,
                                zorder=3,
                                color="black",
                            )

                        plot_kwargs[j][item] = {
                            "marker": "s",
                            "ms": 5.0,
                            "color": plot_obj[0].get_color(),
                        }

                    else:
                        if quantity == "flux":
                            flux_scaling = wavelength

                        if isinstance(box_item.flux[item][0], np.ndarray):
                            if not isinstance(plot_kwargs[j][item], list):
                                raise ValueError(
                                    f"A list with {box_item.flux[item].shape[1]} "
                                    f"dictionaries are required because the filter "
                                    f"{item} has {box_item.flux[item].shape[1]} "
                                    f"values."
                                )

                            for i in range(box_item.flux[item].shape[1]):
                                if "zorder" not in plot_kwargs[j][item][i]:
                                    plot_kwargs[j][item][i]["zorder"] = 3.0

                                ax1.errorbar(
                                    wavelength,
                                    flux_scaling * box_item.flux[item][0, i] / scaling,
                                    xerr=fwhm / 2.0,
                                    yerr=flux_scaling
                                    * box_item.flux[item][1, i]
                                    / scaling,
                                    **plot_kwargs[j][item][i],
                                )

                        else:
                            if box_item.flux[item][1] == 0.0:
                                if "zorder" not in plot_kwargs[j][item]:
                                    plot_kwargs[j][item]["zorder"] = 3.0

                                ax1.errorbar(
                                    wavelength,
                                    flux_scaling * box_item.flux[item][0] / scaling,
                                    xerr=fwhm / 2.0,
                                    yerr=0.5
                                    * flux_scaling
                                    * box_item.flux[item][0]
                                    / scaling,
                                    uplims=True,
                                    capsize=2.0,
                                    capthick=0.0,
                                    **plot_kwargs[j][item],
                                )

                            else:
                                if "zorder" not in plot_kwargs[j][item]:
                                    plot_kwargs[j][item]["zorder"] = 3.0

                                ax1.errorbar(
                                    wavelength,
                                    flux_scaling * box_item.flux[item][0] / scaling,
                                    xerr=fwhm / 2.0,
                                    yerr=flux_scaling
                                    * box_item.flux[item][1]
                                    / scaling,
                                    **plot_kwargs[j][item],
                                )

        elif isinstance(box_item, SynphotBox):
            obj_index = None

            for i, find_item in enumerate(boxes):
                if isinstance(find_item, ObjectBox):
                    obj_index = i
                    break

            for item in box_item.flux:
                transmission = ReadFilter(item)
                wavelength = transmission.mean_wavelength()
                fwhm = transmission.filter_fwhm()

                if quantity == "flux":
                    flux_scaling = wavelength

                if plot_kwargs[j] is not None and item in plot_kwargs[j]:
                    kwargs_copy = plot_kwargs[j][item].copy()

                    if "zorder" not in kwargs_copy:
                        kwargs_copy["zorder"] = 4.0

                    ax1.errorbar(
                        wavelength,
                        flux_scaling * box_item.flux[item] / scaling,
                        xerr=fwhm / 2.0,
                        yerr=None,
                        **kwargs_copy,
                    )

                elif (
                    obj_index is None
                    or not plot_kwargs[obj_index]
                    or item not in plot_kwargs[obj_index]
                ):
                    ax1.errorbar(
                        wavelength,
                        flux_scaling * box_item.flux[item] / scaling,
                        xerr=fwhm / 2.0,
                        yerr=None,
                        alpha=0.7,
                        marker="s",
                        ms=5,
                        zorder=4,
                        mfc="white",
                    )

                else:
                    if isinstance(plot_kwargs[obj_index][item], list):
                        # In case of multiple photometry values for the same filter, use the
                        # plot_kwargs of the first data point

                        kwargs_copy = plot_kwargs[obj_index][item][0].copy()

                        if "label" in kwargs_copy:
                            del kwargs_copy["label"]

                        if "zorder" not in kwargs_copy:
                            kwargs_copy["zorder"] = 4.0

                        ax1.errorbar(
                            wavelength,
                            flux_scaling * box_item.flux[item] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=None,
                            mfc="white",
                            **kwargs_copy,
                        )

                    else:
                        kwargs_copy = plot_kwargs[obj_index][item].copy()

                        if "label" in kwargs_copy:
                            del kwargs_copy["label"]

                        if "mfc" in kwargs_copy:
                            del kwargs_copy["mfc"]

                        if "zorder" not in kwargs_copy:
                            kwargs_copy["zorder"] = 4.0

                        ax1.errorbar(
                            wavelength,
                            flux_scaling * box_item.flux[item] / scaling,
                            xerr=fwhm / 2.0,
                            yerr=None,
                            mfc="white",
                            **kwargs_copy,
                        )

    if filters is not None:
        for i, item in enumerate(filters):
            transmission = ReadFilter(item)
            data = transmission.get_filter()

            ax2.plot(data[:, 0], data[:, 1], "-", lw=0.7, color="tab:gray", zorder=1)

    if residuals is not None:
        obj_index = None

        for i, find_item in enumerate(boxes):
            if isinstance(find_item, ObjectBox):
                obj_index = i
                break

        if obj_index is None:
            raise ValueError(
                "ObjectBox not found so can not create "
                "residuals. Please add an ObjectBox to "
                "the list of boxes."
            )

        res_max = 0.0

        if residuals.photometry is not None:
            for item in residuals.photometry:
                if not plot_kwargs[obj_index] or item not in plot_kwargs[obj_index]:
                    ax3.plot(
                        residuals.photometry[item][0],
                        residuals.photometry[item][1],
                        marker="s",
                        ms=5,
                        linestyle="none",
                        zorder=2,
                    )

                else:
                    if residuals.photometry[item].ndim == 1:
                        if "zorder" not in plot_kwargs[obj_index][item]:
                            plot_kwargs[obj_index][item]["zorder"] = 2.0

                        ax3.errorbar(
                            residuals.photometry[item][0],
                            residuals.photometry[item][1],
                            **plot_kwargs[obj_index][item],
                        )

                    elif residuals.photometry[item].ndim == 2:
                        for i in range(residuals.photometry[item].shape[1]):
                            if isinstance(plot_kwargs[obj_index][item], list):
                                if "zorder" not in plot_kwargs[obj_index][item][i]:
                                    plot_kwargs[obj_index][item][i]["zorder"] = 2.0

                                ax3.errorbar(
                                    residuals.photometry[item][0, i],
                                    residuals.photometry[item][1, i],
                                    **plot_kwargs[obj_index][item][i],
                                )

                            else:
                                if "zorder" not in plot_kwargs[obj_index][item]:
                                    plot_kwargs[obj_index][item]["zorder"] = 2.0

                                ax3.errorbar(
                                    residuals.photometry[item][0, i],
                                    residuals.photometry[item][1, i],
                                    **plot_kwargs[obj_index][item],
                                )

                finite = np.isfinite(residuals.photometry[item][1])

                max_tmp = np.max(np.abs(residuals.photometry[item][1][finite]))

                if max_tmp > res_max:
                    res_max = max_tmp

        if residuals.spectrum is not None:
            for key, value in residuals.spectrum.items():
                if not plot_kwargs[obj_index] or key not in plot_kwargs[obj_index]:
                    ax3.errorbar(
                        value[:, 0], value[:, 1], marker="o", ms=2, ls="none", zorder=1
                    )

                else:
                    if "zorder" not in plot_kwargs[obj_index][key]:
                        plot_kwargs[obj_index][key]["zorder"] = 1.0

                    ax3.errorbar(
                        value[:, 0],
                        value[:, 1],
                        **plot_kwargs[obj_index][key],
                    )

                max_tmp = np.nanmax(np.abs(value[:, 1]))

                if max_tmp > res_max:
                    res_max = max_tmp

        res_lim = math.ceil(1.1 * res_max)

        if res_lim > 10.0:
            res_lim = 5.0

        ax3.axhline(0.0, ls="--", lw=0.7, color="gray", dashes=(2, 4), zorder=0.5)

        if res_lim > 5.0 or (
            ylim_res is not None and ylim_res[0] < -5.0 and ylim_res[1] > 5.0
        ):
            ax3.axhline(-5.0, ls=":", lw=0.7, color="gray", dashes=(1, 4), zorder=0.5)
            ax3.axhline(5.0, ls=":", lw=0.7, color="gray", dashes=(1, 4), zorder=0.5)

        if ylim_res is None:
            ax3.set_ylim(-res_lim, res_lim)

        else:
            ax3.set_ylim(ylim_res[0], ylim_res[1])

    if filters is not None:
        ax2.set_ylim(0.0, 1.1)

    if title is not None:
        if filters:
            ax2.set_title(title, y=1.02, fontsize=13)
        else:
            ax1.set_title(title, y=1.02, fontsize=13)

    handles, labels = ax1.get_legend_handles_labels()

    if handles and legend is not None:
        if isinstance(legend, list):
            model_handles = []
            data_handles = []

            model_labels = []
            data_labels = []

            for i, item in enumerate(handles):
                if isinstance(item, mpl.lines.Line2D):
                    model_handles.append(item)
                    model_labels.append(labels[i])

                elif isinstance(item, mpl.container.ErrorbarContainer):
                    data_handles.append(item)
                    data_labels.append(labels[i])

                else:
                    warnings.warn(
                        f"The object type {item} is not implemented for the legend."
                    )

            if legend[0] is not None:
                if isinstance(legend[0], (str, tuple)):
                    leg_1 = ax1.legend(
                        model_handles,
                        model_labels,
                        loc=legend[0],
                        fontsize=10.0,
                        frameon=False,
                    )
                else:
                    leg_1 = ax1.legend(model_handles, model_labels, **legend[0])

            else:
                leg_1 = None

            if legend[1] is not None:
                if isinstance(legend[1], (str, tuple)):
                    ax1.legend(
                        data_handles,
                        data_labels,
                        loc=legend[1],
                        fontsize=8,
                        frameon=False,
                    )
                else:
                    ax1.legend(data_handles, data_labels, **legend[1])

            if leg_1 is not None:
                ax1.add_artist(leg_1)

        elif isinstance(legend, (str, tuple)):
            ax1.legend(loc=legend, fontsize=8, frameon=False)

        else:
            ax1.legend(**legend)

    if scale[0] == "log":
        ax1.xaxis.set_major_formatter(ScalarFormatter())

        if ax2 is not None:
            ax2.xaxis.set_major_formatter(ScalarFormatter())

        if ax3 is not None:
            ax3.xaxis.set_major_formatter(ScalarFormatter())

    # if scale[1] == "log":
    #     ax1.yaxis.set_major_locator()

    # filters = ['Paranal/SPHERE.ZIMPOL_N_Ha',
    #            'MUSE/Hbeta',
    #            'ALMA/855']
    #
    # filters = ['Paranal/SPHERE.IRDIS_B_Y',
    #            'MKO/NSFCam.J',
    #            'Paranal/SPHERE.IRDIS_D_H23_2',
    #            'Paranal/SPHERE.IRDIS_D_H23_3',
    #            'Paranal/SPHERE.IRDIS_D_K12_1',
    #            'Paranal/SPHERE.IRDIS_D_K12_2',
    #            'Paranal/NACO.Lp',
    #            'Paranal/NACO.NB405',
    #            'Paranal/NACO.Mp']
    #
    # for i, item in enumerate(filters):
    #     readfilter = ReadFilter(item)
    #     filter_wavelength = readfilter.mean_wavelength()
    #     filter_width = readfilter.filter_fwhm()
    #
    #     # if i == 5:
    #     #     ax1.errorbar(filter_wavelength, 1.3e4, xerr=filter_width/2., color='dimgray', elinewidth=2.5, zorder=10)
    #     # else:
    #     #     ax1.errorbar(filter_wavelength, 6e3, xerr=filter_width/2., color='dimgray', elinewidth=2.5, zorder=10)
    #
    #     if i == 0:
    #         ax1.text(filter_wavelength, 1e-2, r'H$\alpha$', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 1:
    #         ax1.text(filter_wavelength, 1e-2, r'H$\beta$', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 2:
    #         ax1.text(filter_wavelength, 1e-2, 'ALMA\nband 7 rms', ha='center', va='center', fontsize=8, color='black')
    #
    #     if i == 0:
    #         ax1.text(filter_wavelength, 1.4, 'Y', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 1:
    #         ax1.text(filter_wavelength, 1.4, 'J', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 2:
    #         ax1.text(filter_wavelength-0.04, 1.4, 'H2', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 3:
    #         ax1.text(filter_wavelength+0.04, 1.4, 'H3', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 4:
    #         ax1.text(filter_wavelength, 1.4, 'K1', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 5:
    #         ax1.text(filter_wavelength, 1.4, 'K2', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 6:
    #         ax1.text(filter_wavelength, 1.4, 'L$\'$', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 7:
    #         ax1.text(filter_wavelength, 1.4, 'NB4.05', ha='center', va='center', fontsize=10, color='black')
    #     elif i == 8:
    #         ax1.text(filter_wavelength, 1.4, 'M$\'}$', ha='center', va='center', fontsize=10, color='black')
    #
    # ax1.text(1.26, 0.58, 'VLT/SPHERE', ha='center', va='center', fontsize=8., color='slateblue', rotation=43.)
    # ax1.text(2.5, 1.28, 'VLT/SINFONI', ha='left', va='center', fontsize=8., color='darkgray')

    if output is None:
        plt.show()
    else:
        print(f"\nOutput: {output}")
        plt.savefig(output, bbox_inches="tight")

    return fig
