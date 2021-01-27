Vivarium MSLT Tobacco Intervention Comparison
=============================================

.. image:: https://readthedocs.org/projects/vivarium-tobacco-intervention-comparison/badge/?version=latest
   :target: https://vivarium-tobacco-intervention-comparison.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://zenodo.org/badge/194912268.svg
   :target: https://zenodo.org/badge/latestdoi/194912268

Research repository for the Vivarium MSLT Tobacco Intervention Comparison
project.

Installation
------------

To set up a new research environment, open up a terminal and run::

    $> conda create --name=mslt_tobacco python=3.6
    ...standard conda install stuff...
    $> conda activate mslt_tobacco
    (mslt_tobacco) $> git clone git@github.com:ihmeuw/unimelb_viv.git
    (mslt_tobacco) $> cd unimelb_viv
    (mslt_tobacco) $> pip install -e .

See the :ref:`getting-started` section of the tutorial for further details.

Testing
------------

simulate run -v model_specifications/house_test.yaml

Working Package List
------------

aiocontextvars==0.2.2
certifi==2020.12.5
click==7.1.2
colorama==0.4.4
contextvars==2.4
decorator==4.4.2
immutables==0.14
Jinja2==2.11.2
loguru==0.5.3
MarkupSafe==1.1.1
networkx==2.5
numexpr==2.7.2
numpy==1.19.5
pandas==1.1.5
python-dateutil==2.8.1
pytz==2020.5
PyYAML==5.4.1
scipy==1.5.4
six==1.15.0
tables==3.6.1
-e git+https://github.com/TimWilsonE/vivarium_unimelb_tobacco_intervention_comparison.git@121c903454f7c2e6116379c46070f91f2bd717f0#egg=unimelb_viv
vivarium==0.10.1
win32-setctime==1.0.3
wincertstore==0.2

