# Copyright 2012 Hewlett-Packard Development Company, L.P.
# Copyright 2012 Varnish Software AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""
Publishers define actions that the Jenkins job should perform after
the build is complete.

**Component**: publishers
  :Macro: publisher
  :Entry Point: jenkins_jobs.publishers

Example::

  job:
    name: test_job

    publishers:
      - scp:
          site: 'example.com'
          source: 'doc/build/html/**/*'
          target_path: 'project'
"""


import xml.etree.ElementTree as XML
import jenkins_jobs.modules.base
import logging


def archive(parser, xml_parent, data):
    """yaml: archive
    Archive build artifacts

    :arg str artifacts: path specifier for artifacts to archive
    :arg str excludes: path specifier for artifacts to exclude
    :arg bool latest_only: only keep the artifacts from the latest
      successful build

    Example::

      publishers:
        - archive:
            artifacts: *.tar.gz
    """
    archiver = XML.SubElement(xml_parent, 'hudson.tasks.ArtifactArchiver')
    artifacts = XML.SubElement(archiver, 'artifacts')
    artifacts.text = data['artifacts']
    if 'excludes' in data:
        excludes = XML.SubElement(archiver, 'excludes')
        excludes.text = data['excludes']
    latest = XML.SubElement(archiver, 'latestOnly')
    latest_only = data.get('latest_only', False)
    if latest_only:
        latest.text = 'true'
    else:
        latest.text = 'false'


def deploy(parser, xml_parent, data):
    """yaml: deploy
    Deploy build artifacts

    :arg str files: comma-seperated list indicating files to deploy
    :arg str remote: path to the remote directory

    """

    deployer = XML.SubElement(xml_parent,
                         'org.jenkinsci.plugins.artifactdeployer.ArtifactDeployerPublisher')
    entries = XML.SubElement(deployer, 'entries')
    entry_e = XML.SubElement(entries,
                'org.jenkinsci.plugins.artifactdeployer.ArtifactDeployerEntry')
    XML.SubElement(entry_e, 'includes').text = data['artifacts']
    XML.SubElement(entry_e, 'remote').text = data['remote']

def trigger_parameterized_builds(parser, xml_parent, data):
    """yaml: trigger-parameterized-builds
    Trigger parameterized builds of other jobs.
    Requires the Jenkins `Parameterized Trigger Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/
    Parameterized+Trigger+Plugin>`_

    :arg str project: name of the job to trigger
    :arg str predefined-parameters: parameters to pass to the other
      job (optional)
    :arg str git-revision: Pass git revision to the other job (optional)
    :arg str condition: when to trigger the other job (default 'ALWAYS')
    :arg str property-file: Use properties from file (optional)

    Example::

      publishers:
        - trigger-parameterized-builds:
            - project: other_job, foo, bar
              predefined-parameters: foo=bar
            - project: other_job1, other_job2
              predefined-parameters: BUILD_NUM=${BUILD_NUMBER}
              property-file: version.prop
            - project: yet_another_job
              predefined-parameters: foo=bar
              git-revision: true

    """
    tbuilder = XML.SubElement(xml_parent,
                              'hudson.plugins.parameterizedtrigger.'
                              'BuildTrigger')
    configs = XML.SubElement(tbuilder, 'configs')
    for project_def in data:
        tconfig = XML.SubElement(configs,
                                 'hudson.plugins.parameterizedtrigger.'
                                 'BuildTriggerConfig')
        tconfigs = XML.SubElement(tconfig, 'configs')
        if ('predefined-parameters' in project_def
            or 'git-revision' in project_def
            or 'property-file' in project_def):

            if 'predefined-parameters' in project_def:
                params = XML.SubElement(tconfigs,
                                        'hudson.plugins.parameterizedtrigger.'
                                        'PredefinedBuildParameters')
                properties = XML.SubElement(params, 'properties')
                properties.text = project_def['predefined-parameters']

            if 'git-revision' in project_def and project_def['git-revision']:
                params = XML.SubElement(tconfigs,
                                        'hudson.plugins.git.'
                                        'GitRevisionBuildParameters')
                properties = XML.SubElement(params, 'combineQueuedCommits')
                properties.text = 'false'
            if 'property-file' in project_def and project_def['property-file']:
                params = XML.SubElement(tconfigs,
                                        'hudson.plugins.parameterizedtrigger.'
                                        'FileBuildParameters')
                properties = XML.SubElement(params, 'propertiesFile')
                properties.text = project_def['property-file']

        else:
            tconfigs.set('class', 'java.util.Collections$EmptyList')
        projects = XML.SubElement(tconfig, 'projects')
        projects.text = project_def['project']
        condition = XML.SubElement(tconfig, 'condition')
        condition.text = project_def.get('condition', 'ALWAYS')
        trigger_with_no_params = XML.SubElement(tconfig,
                                                'triggerWithNoParameters')
        trigger_with_no_params.text = 'false'


def trigger(parser, xml_parent, data):
    """yaml: trigger
    Trigger non-parametrised builds of other jobs.

    :arg str project: name of the job to trigger
    :arg str threshold: when to trigger the other job (default 'SUCCESS'),
      alternatives: SUCCESS, UNSTABLE, FAILURE

    Example::

      publishers:
        - trigger:
            project: other_job
    """
    thresholds = {
        'SUCCESS': {
            'ordinal': '0',
            'color': 'BLUE'
        },
        'UNSTABLE': {
            'ordinal': '1',
            'color': 'YELLOW'
        },
        'FAILURE': {
            'ordinal': '2',
            'color': 'RED'
        }
    }

    tconfig = XML.SubElement(xml_parent, 'hudson.tasks.BuildTrigger')
    childProjects = XML.SubElement(tconfig, 'childProjects')
    childProjects.text = data['project']
    tthreshold = XML.SubElement(tconfig, 'threshold')

    threshold = data.get('threshold', 'SUCCESS')
    if threshold not in thresholds.keys():
        raise Exception("threshold must be one of " +
                        ", ".join(threshold.keys()))
    tname = XML.SubElement(tthreshold, 'name')
    tname.text = threshold
    tordinal = XML.SubElement(tthreshold, 'ordinal')
    tordinal.text = thresholds[threshold]['ordinal']
    tcolor = XML.SubElement(tthreshold, 'color')
    tcolor.text = thresholds[threshold]['color']


def coverage(parser, xml_parent, data):
    """yaml: coverage
    Generate a cobertura coverage report.
    Requires the Jenkins `Cobertura Coverage Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Cobertura+Plugin>`_

    Example::

      publishers:
        - coverage
    """
    cobertura = XML.SubElement(xml_parent,
                               'hudson.plugins.cobertura.CoberturaPublisher')
    XML.SubElement(cobertura, 'coberturaReportFile').text = '**/coverage.xml'
    XML.SubElement(cobertura, 'onlyStable').text = 'false'
    healthy = XML.SubElement(cobertura, 'healthyTarget')
    targets = XML.SubElement(healthy, 'targets', {
        'class': 'enum-map',
        'enum-type': 'hudson.plugins.cobertura.targets.CoverageMetric'})
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'CONDITIONAL'
    XML.SubElement(entry, 'int').text = '70'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'LINE'
    XML.SubElement(entry, 'int').text = '80'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'METHOD'
    XML.SubElement(entry, 'int').text = '80'
    unhealthy = XML.SubElement(cobertura, 'unhealthyTarget')
    targets = XML.SubElement(unhealthy, 'targets', {
        'class': 'enum-map',
        'enum-type': 'hudson.plugins.cobertura.targets.CoverageMetric'})
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'CONDITIONAL'
    XML.SubElement(entry, 'int').text = '0'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'LINE'
    XML.SubElement(entry, 'int').text = '0'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'METHOD'
    XML.SubElement(entry, 'int').text = '0'
    failing = XML.SubElement(cobertura, 'failingTarget')
    targets = XML.SubElement(failing, 'targets', {
        'class': 'enum-map',
        'enum-type': 'hudson.plugins.cobertura.targets.CoverageMetric'})
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'CONDITIONAL'
    XML.SubElement(entry, 'int').text = '0'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'LINE'
    XML.SubElement(entry, 'int').text = '0'
    entry = XML.SubElement(targets, 'entry')
    XML.SubElement(entry, 'hudson.plugins.cobertura.targets.CoverageMetric'
                   ).text = 'METHOD'
    XML.SubElement(entry, 'int').text = '0'
    XML.SubElement(cobertura, 'sourceEncoding').text = 'ASCII'


def ftp(parser, xml_parent, data):
    """yaml: ftp
    Upload files via FTP.
    Requires the Jenkins `Publish over FTP Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Publish+Over+FTP+Plugin>`_

    :arg str site: name of the ftp site
    :arg str target: destination directory
    :arg str source: source path specifier
    :arg str excludes: excluded file pattern (optional)
    :arg str remove-prefix: prefix to remove from uploaded file paths
      (optional)

    Example::

      publishers:
        - ftp:
            site: 'ftp.example.com'
            target: 'dest/dir'
            source: 'base/source/dir/**'
            remove-prefix: 'base/source/dir'
            excludes: '**/*.excludedfiletype'
    """
    console_prefix = 'FTP: '
    plugin_tag = 'jenkins.plugins.publish__over__ftp.BapFtpPublisherPlugin'
    publisher_tag = 'jenkins.plugins.publish__over__ftp.BapFtpPublisher'
    transfer_tag = 'jenkins.plugins.publish__over__ftp.BapFtpTransfer'
    plugin_reference_tag = 'jenkins.plugins.publish_over_ftp.'    \
        'BapFtpPublisherPlugin'
    (_, transfer_node) = base_publish_over(xml_parent,
                                           data,
                                           console_prefix,
                                           plugin_tag,
                                           publisher_tag,
                                           transfer_tag,
                                           plugin_reference_tag)
    XML.SubElement(transfer_node, 'asciiMode').text = 'false'


def junit(parser, xml_parent, data):
    """yaml: junit
    Publish JUnit test results.

    :arg str results: results filename

    Example::

      publishers:
        - junit:
            results: nosetests.xml
    """
    junitresult = XML.SubElement(xml_parent,
                                 'hudson.tasks.junit.JUnitResultArchiver')
    XML.SubElement(junitresult, 'testResults').text = data['results']
    XML.SubElement(junitresult, 'keepLongStdio').text = "true"
    XML.SubElement(junitresult, 'testDataPublishers')


def xunit(parser, xml_parent, data):
    """yaml: xunit
    Publish tests results.  Requires the Jenkins `xUnit Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/xUnit+Plugin>`_

    :arg str thresholdmode: whether thresholds represents an absolute \
    number of tests or a percentage. Either 'number' or 'percent', will \
    default to 'number' if omitted.

    :arg dict thresholds: list containing the thresholds for both \
    'failed' and 'skipped' tests. Each entry should in turn have a \
    list of "threshold name: values". The threshold names are \
    'unstable', 'unstablenew', 'failure', 'failurenew'. Omitting a \
    value will resort on xUnit default value (should be 0).

    :arg dict types: per framework configuration. The key should be \
    one of the internal types we support:\
    'aunit', 'boosttest', 'checktype', 'cpptest', 'cppunit', 'fpcunit', \
    'junit', 'mstest', 'nunit', 'phpunit', 'tusar', 'unittest', 'valgrind'. \
    The 'custom' type is not supported.

    Each framework type can be configured using the following parameters:

    :arg str pattern: An Ant pattern to look for Junit result files, \
    relative to the workspace root.

    :arg bool requireupdate: fail the build whenever fresh tests \
    results have not been found (default: true).

    :arg bool deleteoutput: delete temporary JUnit files (default: true)

    :arg bool stoponerror: Fail the build whenever an error occur during \
    a result file processing (default: true).


    Example::

        publishers:
            - xunit:
                thresholdmode: 'percent'
                thresholds:
                  - failed:
                        unstable: 0
                        unstablenew: 0
                        failure: 0
                        failurenew: 0
                  - skipped:
                        unstable: 0
                        unstablenew: 0
                        failure: 0
                        failurenew: 0
                types:
                  - phpunit:
                      pattern: junit.log
                  - cppUnit:
                      pattern: cppunit.log

    """
    logger = logging.getLogger(__name__)
    xunit = XML.SubElement(xml_parent, 'xunit')

    # Map our internal types to the XML element names used by Jenkins plugin
    types_to_plugin_types = {
        'aunit': 'AUnitJunitHudsonTestType',
        'boosttest': 'AUnitJunitHudsonTestType',
        'checktype': 'CheckType',
        'cpptest': 'CppTestJunitHudsonTestType',
        'cppunit': 'CppUnitJunitHudsonTestType',
        'fpcunit': 'FPCUnitJunitHudsonTestType',
        'junit': 'JUnitType',
        'mstest': 'MSTestJunitHudsonTestType',
        'nunit': 'NUnitJunitHudsonTestType',
        'phpunit': 'PHPUnitJunitHudsonTestType',
        'tusar': 'TUSARJunitHudsonTestType',
        'unittest': 'UnitTestJunitHudsonTestType',
        'valgrind': 'ValgrindJunitHudsonTestType',
        # FIXME should implement the 'custom' type
    }
    implemented_types = types_to_plugin_types.keys()  # shortcut

    # Unit framework we are going to generate xml for
    supported_types = []

    for configured_type in data['types']:
        type_name = configured_type.keys()[0]
        if type_name not in implemented_types:
            logger.warn("Requested xUnit type '%s' is not yet supported" %
                        type_name)
        else:
            # Append for generation
            supported_types.append(configured_type)

    # Generate XML for each of the supported framework types
    for supported_type in supported_types:
        framework_name = supported_type.keys()[0]
        xmltypes = XML.SubElement(xunit, 'types')
        xmlframework = XML.SubElement(xmltypes,
                                      types_to_plugin_types[framework_name])

        XML.SubElement(xmlframework, 'pattern').text = \
            supported_type[framework_name].get('pattern', '')
        XML.SubElement(xmlframework, 'failIfNotNew').text = \
            str(supported_type[framework_name].get(
                'requireupdate', 'true')).lower()
        XML.SubElement(xmlframework, 'deleteOutputFiles').text = \
            str(supported_type[framework_name].get(
                'deleteoutput', 'true')).lower()
        XML.SubElement(xmlframework, 'stopProcessingIfError').text = \
            str(supported_type[framework_name].get(
                'stoponerror', 'true')).lower()

    xmlthresholds = XML.SubElement(xunit, 'thresholds')
    if 'thresholds' in data:
        for t in data['thresholds']:
            if not ('failed' in t or 'skipped' in t):
                logger.warn(
                    "Unrecognized threshold, should be 'failed' or 'skipped'")
                continue
            elname = "org.jenkinsci.plugins.xunit.threshold.%sThreshold" \
                % t.keys()[0].title()
            el = XML.SubElement(xmlthresholds, elname)
            for threshold_name, threshold_value in t.values()[0].items():
                # Normalize and craft the element name for this threshold
                elname = "%sThreshold" % threshold_name.lower().replace(
                    'new', 'New')
                XML.SubElement(el, elname).text = threshold_value

    # Whether to use percent of exact number of tests.
    # Thresholdmode is either:
    # - 1 : absolute (number of tests), default.
    # - 2 : relative (percentage of tests)
    thresholdmode = '1'
    if 'percent' == data.get('thresholdmode', 'number'):
        thresholdmode = '2'
    XML.SubElement(xunit, 'thresholdMode').text = \
        thresholdmode


def _violations_add_entry(xml_parent, name, data):
    vmin = data.get('min', 10)
    vmax = data.get('max', 999)
    vunstable = data.get('unstable', 999)
    pattern = data.get('pattern', None)

    entry = XML.SubElement(xml_parent, 'entry')
    XML.SubElement(entry, 'string').text = name
    tconfig = XML.SubElement(entry, 'hudson.plugins.violations.TypeConfig')
    XML.SubElement(tconfig, 'type').text = name
    XML.SubElement(tconfig, 'min').text = str(vmin)
    XML.SubElement(tconfig, 'max').text = str(vmax)
    XML.SubElement(tconfig, 'unstable').text = str(vunstable)
    XML.SubElement(tconfig, 'usePattern').text = 'false'
    if pattern:
        XML.SubElement(tconfig, 'pattern').text = pattern
    else:
        XML.SubElement(tconfig, 'pattern')


def violations(parser, xml_parent, data):
    """yaml: violations
    Publish code style violations.
    Requires the Jenkins `Violations Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Violations>`_

    The violations component accepts any number of dictionaries keyed
    by the name of the violations system.  The dictionary has the
    following values:

    :arg int min: sunny threshold
    :arg int max: stormy threshold
    :arg int unstable: unstable threshold
    :arg str pattern: report filename pattern

    Any system without a dictionary provided will use default values.

    Valid systems are:

      checkstyle, codenarc, cpd, cpplint, csslint, findbugs, fxcop,
      gendarme, jcreport, jslint, pep8, pmd, pylint, simian, stylecop

    Example::

      publishers:
        - violations:
            pep8:
              min: 0
              max: 1
              unstable: 1
              pattern: '**/pep8.txt'
    """
    violations = XML.SubElement(xml_parent,
                                'hudson.plugins.violations.'
                                'ViolationsPublisher')
    config = XML.SubElement(violations, 'config')
    suppressions = XML.SubElement(config, 'suppressions',
                                  {'class': 'tree-set'})
    XML.SubElement(suppressions, 'no-comparator')
    configs = XML.SubElement(config, 'typeConfigs')
    XML.SubElement(configs, 'no-comparator')

    for name in [
        'checkstyle',
        'codenarc',
        'cpd',
        'cpplint',
        'csslint',
        'findbugs',
        'fxcop',
        'gendarme',
        'jcreport',
        'jslint',
        'pep8',
        'pmd',
        'pylint',
        'simian',
        'stylecop']:
        _violations_add_entry(configs, name, data.get(name, {}))

    XML.SubElement(config, 'limit').text = '100'
    XML.SubElement(config, 'sourcePathPattern')
    XML.SubElement(config, 'fauxProjectPath')
    XML.SubElement(config, 'encoding').text = 'default'


def checkstyle(parser, xml_parent, data):
    """yaml: checkstyle
    Publish trend reports with Checkstyle.
    Requires the `Checkstyle Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Checkstyle+Plugin>`_

    The checkstyle component accepts a dictionary with the
    following values:

    :arg str pattern: report filename pattern
    :arg bool canRunOnFailed: also runs for failed builds
     (instead of just stable or unstable builds)
    :arg bool shouldDetectModules:
    :arg int healthy: sunny threshold
    :arg int unHealthy: stormy threshold
    :arg str healthThreshold: threshold priority for health status
     (high: only high, normal: high and normal, low: all)
    :arg dict thresholds:
        :thresholds:
            * **unstable** (`dict`)
                :unstable: * **totalAll** (`int`)
                           * **totalHigh** (`int`)
                           * **totalNormal** (`int`)
                           * **totalLow** (`int`)
            * **failed** (`dict`)
                :failed: * **totalAll** (`int`)
                         * **totalHigh** (`int`)
                         * **totalNormal** (`int`)
                         * **totalLow** (`int`)
    :arg str defaultEncoding: encoding for parsing or showing files
     (empty will use platform default)

    Example::

      publishers:
        - checkstyle:
            pattern: '**/checkstyle-result.xml'
            healthy: 0
            unHealthy: 100
            healthThreshold: 'high'
            thresholds:
                unstable:
                    totalHigh: 10
                failed:
                    totalHigh: 1
    """
    checkstyle = XML.SubElement(xml_parent,
                                'hudson.plugins.checkstyle.'
                                'CheckStylePublisher')

    dval = data.get('healthy', None)
    if dval:
        XML.SubElement(checkstyle, 'healthy').text = str(dval)
    else:
        XML.SubElement(checkstyle, 'healthy')

    dval = data.get('unHealthy', None)
    if dval:
        XML.SubElement(checkstyle, 'unHealthy').text = str(dval)
    else:
        XML.SubElement(checkstyle, 'unHealthy')

    XML.SubElement(checkstyle, 'thresholdLimit').text = \
        data.get('healthThreshold', 'low')

    XML.SubElement(checkstyle, 'pluginName').text = '[CHECKSTYLE] '

    XML.SubElement(checkstyle, 'defaultEncoding').text = \
        data.get('defaultEncoding', '')

    if data.get('canRunOnFailed', False):
        XML.SubElement(checkstyle, 'canRunOnFailed').text = 'true'
    else:
        XML.SubElement(checkstyle, 'canRunOnFailed').text = 'false'

    XML.SubElement(checkstyle, 'useStableBuildAsReference').text = 'false'

    XML.SubElement(checkstyle, 'useDeltaValues').text = 'false'

    dthresholds = data.get('thresholds', {})
    dunstable = dthresholds.get('unstable', {})
    dfailed = dthresholds.get('failed', {})
    thresholds = XML.SubElement(checkstyle, 'thresholds')

    dval = dunstable.get('totalAll', None)
    if dval:
        XML.SubElement(thresholds, 'unstableTotalAll').text = str(dval)
    else:
        XML.SubElement(thresholds, 'unstableTotalAll')

    dval = dunstable.get('totalHigh', None)
    if dval:
        XML.SubElement(thresholds, 'unstableTotalHigh').text = str(dval)
    else:
        XML.SubElement(thresholds, 'unstableTotalHigh')

    dval = dunstable.get('totalNormal', None)
    if dval:
        XML.SubElement(thresholds, 'unstableTotalNormal').text = str(dval)
    else:
        XML.SubElement(thresholds, 'unstableTotalNormal')

    dval = dunstable.get('totalLow', None)
    if dval:
        XML.SubElement(thresholds, 'unstableTotalLow').text = str(dval)
    else:
        XML.SubElement(thresholds, 'unstableTotalLow')

    dval = dfailed.get('totalAll', None)
    if dval:
        XML.SubElement(thresholds, 'failedTotalAll').text = str(dval)
    else:
        XML.SubElement(thresholds, 'failedTotalAll')

    dval = dfailed.get('totalHigh', None)
    if dval:
        XML.SubElement(thresholds, 'failedTotalHigh').text = str(dval)
    else:
        XML.SubElement(thresholds, 'failedTotalHigh')

    dval = dfailed.get('totalNormal', None)
    if dval:
        XML.SubElement(thresholds, 'failedTotalNormal').text = str(dval)
    else:
        XML.SubElement(thresholds, 'failedTotalNormal')

    dval = dfailed.get('totalLow', None)
    if dval:
        XML.SubElement(thresholds, 'failedTotalLow').text = str(dval)
    else:
        XML.SubElement(thresholds, 'failedTotalLow')

    if data.get('shouldDetectModules', False):
        XML.SubElement(checkstyle, 'shouldDetectModules').text = 'true'
    else:
        XML.SubElement(checkstyle, 'shouldDetectModules').text = 'false'

    XML.SubElement(checkstyle, 'dontComputeNew').text = 'true'

    XML.SubElement(checkstyle, 'doNotResolveRelativePaths').text = 'false'

    XML.SubElement(checkstyle, 'pattern').text = data.get('pattern', '')


def scp(parser, xml_parent, data):
    """yaml: scp
    Upload files via SCP
    Requires the Jenkins `SCP Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/SCP+plugin>`_

    :arg str site: name of the scp site
    :arg str target: destination directory
    :arg str source: source path specifier
    :arg bool keep-hierarchy: keep the file hierarchy when uploading
      (default false)
    :arg bool copy-after-failure: copy files even if the job fails
      (default false)
    :arg bool copy-console: copy the console log (default false); if
      specified, omit 'target'

    Example::

      publishers:
        - scp:
            site: 'example.com'
            target: 'dest/dir'
            source: 'base/source/dir/**'
    """
    site = data['site']
    scp = XML.SubElement(xml_parent,
                         'be.certipost.hudson.plugin.SCPRepositoryPublisher')
    XML.SubElement(scp, 'siteName').text = site
    entries = XML.SubElement(scp, 'entries')
    for entry in data['files']:
        entry_e = XML.SubElement(entries, 'be.certipost.hudson.plugin.Entry')
        XML.SubElement(entry_e, 'filePath').text = entry['target']
        XML.SubElement(entry_e, 'sourceFile').text = entry.get('source', '')
        if entry.get('keep-hierarchy', False):
            XML.SubElement(entry_e, 'keepHierarchy').text = 'true'
        else:
            XML.SubElement(entry_e, 'keepHierarchy').text = 'false'
        if entry.get('copy-console', False):
            XML.SubElement(entry_e, 'copyConsoleLog').text = 'true'
        else:
            XML.SubElement(entry_e, 'copyConsoleLog').text = 'false'
        if entry.get('copy-after-failure', False):
            XML.SubElement(entry_e, 'copyAfterFailure').text = 'true'
        else:
            XML.SubElement(entry_e, 'copyAfterFailure').text = 'false'


def pipeline(parser, xml_parent, data):
    """yaml: pipeline
    Specify a downstream project in a pipeline.
    Requires the Jenkins `Build Pipeline Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Build+Pipeline+Plugin>`_

    :Parameter: the name of the downstream project

    Example::

      publishers:
        - pipleline: deploy

    You can build pipeline jobs that are re-usable in different pipelines by
    using a :ref:`job-template` to define the pipeline jobs,
    and variable substitution to specify the name of
    the downstream job in the pipeline.
    Job-specific substitutions are useful here (see :ref:`project`).

    See 'samples/pipeline.yaml' for an example pipeline implementation.
    """
    if data != '':
        pippub = XML.SubElement(xml_parent,
                                'au.com.centrumsystems.hudson.plugin.'
                                'buildpipeline.trigger.BuildPipelineTrigger')
        XML.SubElement(pippub, 'downstreamProjectNames').text = data


def email(parser, xml_parent, data):
    """yaml: email
    Email notifications on build failure.

    :arg str recipients: Recipient email addresses
    :arg bool notify-every-unstable-build: Send an email for every
      unstable build (default true)
    :arg bool send-to-individuals: Send an email to the individual
      who broke the build (default false)

    Example::

      publishers:
        - email:
            recipients: breakage@example.com
    """

    # TODO: raise exception if this is applied to a maven job
    mailer = XML.SubElement(xml_parent,
                            'hudson.tasks.Mailer')
    XML.SubElement(mailer, 'recipients').text = data['recipients']

    # Note the logic reversal (included here to match the GUI
    if data.get('notify-every-unstable-build', True):
        XML.SubElement(mailer, 'dontNotifyEveryUnstableBuild').text = 'false'
    else:
        XML.SubElement(mailer, 'dontNotifyEveryUnstableBuild').text = 'true'
    XML.SubElement(mailer, 'sendToIndividuals').text = str(
        data.get('send-to-individuals', False)).lower()


def claim_build(parser, xml_parent, data):
    """yaml: claim-build
    Claim build failures
    Requires the Jenkins `Claim Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Claim+plugin>`_

    Example::

      publishers:
        - claim-build
    """

    XML.SubElement(xml_parent, 'hudson.plugins.claim.ClaimPublisher')


def base_email_ext(parser, xml_parent, data, ttype):
    trigger = XML.SubElement(xml_parent,
                             'hudson.plugins.emailext.plugins.trigger.'
                             + ttype)
    email = XML.SubElement(trigger, 'email')
    XML.SubElement(email, 'recipientList').text = ''
    XML.SubElement(email, 'subject').text = '$PROJECT_DEFAULT_SUBJECT'
    XML.SubElement(email, 'body').text = '$PROJECT_DEFAULT_CONTENT'
    XML.SubElement(email, 'sendToDevelopers').text = 'false'
    XML.SubElement(email, 'sendToRequester').text = 'false'
    XML.SubElement(email, 'includeCulprits').text = 'false'
    XML.SubElement(email, 'sendToRecipientList').text = 'true'


def email_ext(parser, xml_parent, data):
    """yaml: email-ext
    Extend Jenkin's built in email notification
    Requires the Jenkins `Email-ext Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Email-ext+plugin>`_

    :arg str recipients: Comma separated list of emails
    :arg str subject: Subject for the email, can include variables like
        ${BUILD_NUMBER} or even groovy or javascript code
    :arg str body: Content for the body of the email, can include variables
        like ${BUILD_NUMBER}, but the real magic is using groovy or
        javascript to hook into the Jenkins API itself
    :arg bool unstable: Send an email for an unstable result (default false)
    :arg bool first-failure: Send an email for just the first failure
        (default false)
    :arg bool not-built: Send an email if not built (default false)
    :arg bool aborted: Send an email if the build is aborted (default false)
    :arg bool regression: Send an email if there is a regression
        (default false)
    :arg bool failure: Send an email if the build fails (default true)
    :arg bool improvement: Send an email if the build improves (default false)
    :arg bool still-failing: Send an email if the build is still failing
        (default false)
    :arg bool success: Send an email for a successful build (default false)
    :arg bool fixed: Send an email if the build is fixed (default false)
    :arg bool still-unstable: Send an email if the build is still unstable
        (default false)
    :arg bool pre-build: Send an email before the build (default false)
    :arg matrixTriggerMode string: BOTH, ONLY_PARENT, ONLY_CONFIGURATION (default BOTH)

    Example::

      publishers:
        - email-ext:
            recipients: foo@example.com, bar@example.com
            subject: Subject for Build ${BUILD_NUMBER}
            body: The build has finished
            unstable: true
            first-failure: true
            not-built: true
            aborted: true
            regression: true
            failure: true
            improvement: true
            still-failing: true
            success: true
            fixed: true
            still-unstable: true
            pre-build: true
    """
    emailext = XML.SubElement(xml_parent,
                              'hudson.plugins.emailext.ExtendedEmailPublisher')
    if 'recipients' in data:
        XML.SubElement(emailext, 'recipientList').text = data['recipients']
    else:
        XML.SubElement(emailext, 'recipientList').text = '$DEFAULT_RECIPIENTS'
    ctrigger = XML.SubElement(emailext, 'configuredTriggers')
    if data.get('unstable', False):
        base_email_ext(parser, ctrigger, data, 'UnstableTrigger')
    if data.get('first-failure', False):
        base_email_ext(parser, ctrigger, data, 'FirstFailureTrigger')
    if data.get('not-built', False):
        base_email_ext(parser, ctrigger, data, 'NotBuiltTrigger')
    if data.get('aborted', False):
        base_email_ext(parser, ctrigger, data, 'AbortedTrigger')
    if data.get('regression', False):
        base_email_ext(parser, ctrigger, data, 'RegressionTrigger')
    if data.get('failure', True):
        base_email_ext(parser, ctrigger, data, 'FailureTrigger')
    if data.get('improvement', False):
        base_email_ext(parser, ctrigger, data, 'ImprovementTrigger')
    if data.get('still-failing', False):
        base_email_ext(parser, ctrigger, data, 'StillFailingTrigger')
    if data.get('success', False):
        base_email_ext(parser, ctrigger, data, 'SuccessTrigger')
    if data.get('fixed', False):
        base_email_ext(parser, ctrigger, data, 'FixedTrigger')
    if data.get('still-unstable', False):
        base_email_ext(parser, ctrigger, data, 'StillUnstableTrigger')
    if data.get('pre-build', False):
        base_email_ext(parser, ctrigger, data, 'PreBuildTrigger')
    XML.SubElement(emailext, 'contentType').text = 'default'
    XML.SubElement(emailext, 'defaultSubject').text = data.get(
        'subject', '$DEFAULT_SUBJECT')
    XML.SubElement(emailext, 'defaultContent').text = data.get(
        'body', '$DEFAULT_CONTENT')
    XML.SubElement(emailext, 'attachmentsPattern').text = ''
    XML.SubElement(emailext, 'presendScript').text = ''
    XML.SubElement(emailext, 'matrixTriggerMode').text = data.get('matrixTriggerMode', 'BOTH')


def fingerprint(parser, xml_parent, data):
    """yaml: fingerprint
    Fingerprint files to track them across builds

    :arg str files: files to fingerprint, follows the @includes of Ant fileset
        (default is blank)
    :arg bool record-artifacts: fingerprint all archived artifacts
        (default false)

    Example::

      publishers:
        - fingerprint:
            files: builddir/test*.xml
            record-artifacts: false
    """
    finger = XML.SubElement(xml_parent, 'hudson.tasks.Fingerprinter')
    XML.SubElement(finger, 'targets').text = data.get('files', '')
    XML.SubElement(finger, 'recordBuildArtifacts').text = str(data.get(
        'record-artifacts', False)).lower()


def aggregate_tests(parser, xml_parent, data):
    """yaml: aggregate-tests
    Aggregate downstream test results

    :arg bool include-failed-builds: whether to include failed builds

    Example::

      publishers:
        - aggregate-tests:
            include-failed-builds: true
    """
    agg = XML.SubElement(xml_parent,
                         'hudson.tasks.test.AggregatedTestResultPublisher')
    XML.SubElement(agg, 'includeFailedBuilds').text = str(data.get(
        'include-failed-builds', False)).lower()


def cppcheck(parser, xml_parent, data):
    """yaml: cppcheck
    Cppcheck result publisher
    Requires the Jenkins `Cppcheck Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Cppcheck+Plugin>`_

    :arg str pattern: file pattern for cppcheck xml report

    for more optional parameters see the example

    Example::

      publishers:
        - cppcheck:
            pattern: "**/cppcheck.xml"
            # the rest is optional
            # build status (new) error count thresholds
            thresholds:
              unstable: 5
              new-unstable: 5
              failure: 7
              new-failure: 3
              # severities which count towards the threshold, default all true
              severity:
                error: true
                warning: true
                information: false
            graph:
              xysize: [500, 200]
              # which errors to display, default only sum
              display:
                sum: false
                error: true
    """
    cppextbase = XML.SubElement(xml_parent,
                                'org.jenkinsci.plugins.cppcheck.'
                                'CppcheckPublisher')
    cppext = XML.SubElement(cppextbase, 'cppcheckConfig')
    XML.SubElement(cppext, 'pattern').text = data['pattern']
    XML.SubElement(cppext, 'ignoreBlankFiles').text = \
        str(data.get('ignoreblankfiles', 'false')).lower()

    csev = XML.SubElement(cppext, 'configSeverityEvaluation')
    thrsh = data.get('thresholds', {})
    XML.SubElement(csev, 'threshold').text = str(thrsh.get('unstable', ''))
    XML.SubElement(csev, 'newThreshold').text = \
        str(thrsh.get('new-unstable', ''))
    XML.SubElement(csev, 'failureThreshold').text = \
        str(thrsh.get('failure', ''))
    XML.SubElement(csev, 'newFailureThreshold').text = \
        str(thrsh.get('new-failure', ''))
    XML.SubElement(csev, 'healthy').text = str(thrsh.get('healthy', ''))
    XML.SubElement(csev, 'unHealthy').text = str(thrsh.get('unhealthy', ''))

    sev = thrsh.get('severity', {})
    XML.SubElement(csev, 'severityError').text = \
        str(sev.get('error', 'true')).lower()
    XML.SubElement(csev, 'severityWarning').text = \
        str(sev.get('warning', 'true')).lower()
    XML.SubElement(csev, 'severityStyle').text = \
        str(sev.get('style', 'true')).lower()
    XML.SubElement(csev, 'severityPerformance').text = \
        str(sev.get('performance', 'true')).lower()
    XML.SubElement(csev, 'severityInformation').text = \
        str(sev.get('information', 'true')).lower()

    graph = data.get('graph', {})
    cgraph = XML.SubElement(cppext, 'configGraph')
    x, y = graph.get('xysize', [500, 200])
    XML.SubElement(cgraph, 'xSize').text = str(x)
    XML.SubElement(cgraph, 'ySize').text = str(y)
    gdisplay = graph.get('display', {})
    XML.SubElement(cgraph, 'displayAllErrors').text = \
        str(gdisplay.get('sum', 'true')).lower()
    XML.SubElement(cgraph, 'displayErrorSeverity').text = \
        str(gdisplay.get('error', 'false')).lower()
    XML.SubElement(cgraph, 'displayWarningSeverity').text = \
        str(gdisplay.get('warning', 'false')).lower()
    XML.SubElement(cgraph, 'displayStyleSeverity').text = \
        str(gdisplay.get('style', 'false')).lower()
    XML.SubElement(cgraph, 'displayPerformanceSeverity').text = \
        str(gdisplay.get('performance', 'false')).lower()
    XML.SubElement(cgraph, 'displayInformationSeverity').text = \
        str(gdisplay.get('information', 'false')).lower()


def logparser(parser, xml_parent, data):
    """yaml: logparser
    Requires the Jenkins `Log Parser Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Log+Parser+Plugin>`_

    :arg str parse-rules: full path to parse rules
    :arg bool unstable-on-warning: mark build unstable on warning
    :arg bool fail-on-error: mark build failed on error

    Example::
      publishers:
        - logparser:
            parse-rules: "/path/to/parserules"
            unstable-on-warning: true
            fail-on-error: true
    """

    clog = XML.SubElement(xml_parent,
                          'hudson.plugins.logparser.LogParserPublisher')
    XML.SubElement(clog, 'unstableOnWarning').text = \
        str(data.get('unstable-on-warning', 'false')).lower()
    XML.SubElement(clog, 'failBuildOnError').text = \
        str(data.get('fail-on-error', 'false')).lower()
    # v1.08: this must be the full path, the name of the rules is not enough
    XML.SubElement(clog, 'parsingRulesPath').text = data.get('parse-rules', '')


def copy_to_master(parser, xml_parent, data):
    """yaml: copy-to-master
    Copy files to master from slave
    Requires the Jenkins `Copy To Slave Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Copy+To+Slave+Plugin>`_

    :arg list includes: list of file patterns to copy
    :arg list excludes: list of file patterns to exclude
    :arg string destination: absolute path into which the files will be copied.
                             If left blank they will be copied into the
                             workspace of the current job

    Example::

      publishers:
        - copy-to-master:
            includes:
              - file1
              - file2*.txt
            excludes:
              - file2bad.txt
    """
    p = 'com.michelin.cio.hudson.plugins.copytoslave.CopyToMasterNotifier'
    cm = XML.SubElement(xml_parent, p)

    XML.SubElement(cm, 'includes').text = ','.join(data.get('includes', ['']))
    XML.SubElement(cm, 'excludes').text = ','.join(data.get('excludes', ['']))

    XML.SubElement(cm, 'destinationFolder').text = \
        data.get('destination', '')

    if data.get('destination', ''):
        XML.SubElement(cm, 'overrideDestinationFolder').text = 'true'


def jira(parser, xml_parent, data):
    """yaml: jira
    Update relevant JIRA issues
    Requires the Jenkins `JIRA Plugin
    <https://wiki.jenkins-ci.org/display/JENKINS/JIRA+Plugin>`_

    Example::

      publishers:
        - jira
    """
    XML.SubElement(xml_parent, 'hudson.plugins.jira.JiraIssueUpdater')


def groovy_postbuild(parser, xml_parent, data):
    """yaml: groovy-postbuild
    Execute a groovy script.
    Requires the Jenkins `Groovy Postbuild Plugin
    <https://wiki.jenkins-ci.org/display/JENKINS/Groovy+Postbuild+Plugin>`_

    :Parameter: the groovy script to execute

    Example::

      publishers:
        - groovy-postbuild: "manager.buildFailure()"

    """
    root_tag = 'org.jvnet.hudson.plugins.groovypostbuild.'\
        'GroovyPostbuildRecorder'
    groovy = XML.SubElement(xml_parent, root_tag)
    XML.SubElement(groovy, 'groovyScript').text = data


def base_publish_over(xml_parent, data, console_prefix,
                      plugin_tag, publisher_tag,
                      transferset_tag, reference_plugin_tag):
    outer = XML.SubElement(xml_parent, plugin_tag)
    XML.SubElement(outer, 'consolePrefix').text = console_prefix
    delegate = XML.SubElement(outer, 'delegate')
    publishers = XML.SubElement(delegate, 'publishers')
    inner = XML.SubElement(publishers, publisher_tag)
    XML.SubElement(inner, 'configName').text = data['site']
    XML.SubElement(inner, 'verbose').text = 'true'

    transfers = XML.SubElement(inner, 'transfers')
    transfersset = XML.SubElement(transfers, transferset_tag)
    XML.SubElement(transfersset, 'remoteDirectory').text = data['target']
    XML.SubElement(transfersset, 'sourceFiles').text = data['source']
    XML.SubElement(transfersset, 'excludes').text = data.get('excludes', '')
    XML.SubElement(transfersset, 'removePrefix').text = \
        data.get('remove-prefix', '')
    XML.SubElement(transfersset, 'remoteDirectorySDF').text = 'false'
    XML.SubElement(transfersset, 'flatten').text = 'false'
    XML.SubElement(transfersset, 'cleanRemote').text = 'false'

    XML.SubElement(inner, 'useWorkspaceInPromotion').text = 'false'
    XML.SubElement(inner, 'usePromotionTimestamp').text = 'false'
    XML.SubElement(delegate, 'continueOnError').text = 'false'
    XML.SubElement(delegate, 'failOnError').text = 'false'
    XML.SubElement(delegate, 'alwaysPublishFromMaster').text = 'false'
    XML.SubElement(delegate, 'hostConfigurationAccess',
                   {'class': reference_plugin_tag,
                    'reference': '../..'})
    return (outer, transfersset)


def cifs(parser, xml_parent, data):
    """yaml: cifs
    Upload files via CIFS.
    Requires the Jenkins `Publish over CIFS Plugin.
    <https://wiki.jenkins-ci.org/display/JENKINS/Publish+Over+CIFS+Plugin>`_

    :arg str site: name of the cifs site/share
    :arg str target: destination directory
    :arg str source: source path specifier
    :arg str excludes: excluded file pattern (optional)
    :arg str remove-prefix: prefix to remove from uploaded file paths
      (optional)

    Example::

      publishers:
        - cifs:
            site: 'cifs.share'
            target: 'dest/dir'
            source: 'base/source/dir/**'
            remove-prefix: 'base/source/dir'
            excludes: '**/*.excludedfiletype'
    """
    console_prefix = 'CIFS: '
    plugin_tag = 'jenkins.plugins.publish__over__cifs.CifsPublisherPlugin'
    publisher_tag = 'jenkins.plugins.publish__over__cifs.CifsPublisher'
    transfer_tag = 'jenkins.plugins.publish__over__cifs.CifsTransfer'
    plugin_reference_tag = 'jenkins.plugins.publish_over_cifs.'    \
        'CifsPublisherPlugin'
    base_publish_over(xml_parent,
                      data,
                      console_prefix,
                      plugin_tag,
                      publisher_tag,
                      transfer_tag,
                      plugin_reference_tag)


class Publishers(jenkins_jobs.modules.base.Base):
    sequence = 70

    def gen_xml(self, parser, xml_parent, data):
        publishers = XML.SubElement(xml_parent, 'publishers')

        for action in data.get('publishers', []):
            self._dispatch('publisher', 'publishers',
                           parser, publishers, action)
