=================
Converting Models
=================

pybdsim provdies converters to allow BDSIM models to prepared from optical
descriptions of accelerators in other formats such as MADX and MAD8.

The following converters are provided and described here:


* MADX to BDSIM
  
  * `MadxTfs2Gmad`_
  * `MadxTfs2GmadStrength`_
* MAD8 to BDSIM
  
  * `Mad8Twiss2Gmad`_
  * `Mad8Saveline2Gmad`_
* Transport to BDSIM
  
  * `pytransport`_
* BDSIM Primary Particle Conversion
  
  * `BDSIM Primaries To Others`_


MadxTfs2Gmad
------------

A MADX lattice can be easily converted to a BDSIM gmad input file using the supplied
python utilities. This is achieved by

1. preparing a tfs file with madx containing all twiss table information
2. converting the tfs file to gmad using pybdsim

Preparing a Tfs File
********************

The twiss file can be prepared by appending the following MADX syntax to the
end of your MADX script::

  select,flag=twiss, clear; 
  twiss,sequence=SEQUENCENAME, file=twiss.tfs;

where `SEQUENCENAME` is the name of the sequence in madx. By not specifying the output
columns, a very large file is produced containing all possible columns.  This is required
to successfully convert the lattice.  If the tfs file contains insufficient information,
pybdsim will not be able to convert the model.

.. note:: The python utilities require "`.tfs`" suffix as the file type to work properly.

Converting the Tfs File
***********************

Once prepared, the Tfs file can be converted. The converter is used as follows::

  >>> pybdsim.Convert.MadxTfs2Gmad('inputfile.tfs', 'latticev1')

The conversion returns typically two objects, which are the :code:`pybdsim.Builder.Machine`
instance and a list of any ommitted items by name. ::

  >>> a,o = pybdsim.Convert.MadxTfs2Gmad('inputfile.tfs', 'latticev1')

where `latticev1` is the output name of the converted model. The user may convert
only part of the input model by specifying `startname` and `stopname`.
The full list of options is described in :ref:`pybdsim-convert`.

Generally speaking, extra information can be folded into the conversion via a user
supplied dictionary with extra parameters for a particular element by name. For a
given element, for example 'drift123', extra parameters can be speficied in a dictionary.
This leads to a dictionary of dictionaries being supplied. This is a relatively simple
structure the user may prepare from their own input format and converters in Python.
For example::

  >>> drift123dict = {'aper1':0.03, 'aper2':0.05, 'apertureType':'rectangular'}
  >>> quaddict = {'magnetGeometryType':'polesfacetcrop}
  >>> d = {'drift123':drift123dict, 'qf1x':quaddict}
  >>> a,o = pybdsim.Convert.MadxTfs2Gmad('inputfile.tfs', 'latticev1', userdict=d)


.. note:: The name must match the name given in the MADX file exactly.

Specific arguments may be given for aperture (`aperturedict`), or for collimation
(`collimatordict`), which are used specifically for those purposes.

There are quite a few options and these are described in :ref:`pybdsim-convert`.

.. note:: The BDSIM-provided pymadx package is required for this conversion to work.

.. note:: The converter will alter the names to remove forbidden characters in names
	  in BDSIM such as '$' or '!'.

Preparation of a Small Section
******************************

For large accelerators, it is often required to model only a small part of the machine.
We recommend generating a Tfs file for the full lattice by default and trimming as
required. The pymadx.Data.Tfs class provides an easy interface for trimming lattices.
The first argument to the pybdsim.Convert.MadxTfs2Gmad function can be either a string
describing the file location or a pymadx.Data.Tfs instance. The following example
trims a lattice to only the first 100 elements::

  >>> a = pymadx.Data.Tfs("twiss_v5.2.tfs")
  >>> b = a[:100]
  >>> m,o = pybdsim.Convert.MadxTfs2Gmad(b, 'v5.2a')

	  
MadxTfs2GmadStrength
--------------------

This is a utility to prepare a strength file file from a Tfs file. The output gmad
file may then be included in an existing BDSIM gmad model after the lattice definition
which will update the strengths of all the magnets.

Mad8Twiss2Gmad
--------------

.. note:: This requires the `<https://bitbucket.org/jairhul/pymad8>`_ package.

Mad8Saveline2Gmad
-----------------

.. note:: This requires the `<https://bitbucket.org/jairhul/pymad8>`_ package.

pytransport
-----------

`<https://bitbucket.org/jairhul/pytransport>`_ is a separate utility to convert transport
models into BDSIM ones.


BDSIM Primaries To Others
-------------------------

The primary particle coordinates generated by BDSIM may be read from an output
ROOT file and written to another format to ensure the exact same coordinates
are used in both simulations. This is typically used for comparison with PTC.
