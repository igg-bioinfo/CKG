"""
    **import.py**
    Generates all the import files: Ontologies, Databases and Experiments.
    The module is reponsible for generating all the csv files that will
    be loaded into the Graph database and also updates a stats object
    (hdf table) with the number of entities and relationships from each
    dataset imported. A new stats object is created the first time a
    full import is run.
"""
import os.path
from datetime import datetime
import pandas as pd
from joblib import Parallel, delayed
import config
from KnowledgeGrapher.ontologies import ontologieshandler as oh, ontologies_config as oconfig
from KnowledgeGrapher.databases import databaseshandler as dh, databases_config as dbconfig
from KnowledgeGrapher.experiments import experimentshandler as eh, experiments_config as econfig
from KnowledgeGrapher import utils

START_TIME = datetime.now()


def ontologiesImport(importDirectory, ontologies=None):
    """
    Generates all the entities and relationships
    from the provided ontologies. If the ontologies list is
    not provided, then all the ontologies listed in the configuration
    will be imported (full_import).
    This function also updates the stats object with numbers from the
    imported ontologies
    Args:
        importDirectory (string): path of the import directory where
                                files will be created
        ontologies (list): A list of ontology names to be imported
    """
    #Ontologies
    ontologiesImportDirectory = os.path.join(importDirectory, oconfig.ontologiesImportDir)
    utils.checkDirectory(ontologiesImportDirectory)
    stats = oh.generateGraphFiles(ontologiesImportDirectory, ontologies)
    statsDf = generateStatsDataFrame(stats)
    writeStats(statsDf)

def databasesImport(importDirectory, databases=None, n_jobs=1):
    """
    Generates all the entities and relationships
    from the provided databases. If the databases list is
    not provided, then all the databases listed in the configuration
    will be imported (full_import).
    This function also updates the stats object with numbers from the
    imported databases.
    Args:
        importDirectory (string): path of the import directory where
                                files will be created
        databases (list): A list of database names to be imported
        n_jobs (int): Number of jobs to run in parallel. 1 by default
                    when updating one database
    """
    #Databases
    databasesImportDirectory = os.path.join(importDirectory, dbconfig.databasesImportDir)
    utils.checkDirectory(databasesImportDirectory)
    stats = dh.generateGraphFiles(databasesImportDirectory, databases, n_jobs)
    statsDf = generateStatsDataFrame(stats)
    writeStats(statsDf)

def experimentsImport(projects=None, n_jobs=1):
    """
    Generates all the entities and relationships
    from the specified Projects. If the projects list is
    not provided, then all the projects the experiments directory
    will be imported (full_import). Calls function experimentImport.
    Args:
        projects (list): A list of project identifiers to be imported
        n_jobs (int): Number of jobs to run in parallel. 1 by default
                    when updating one project
    """
    #Experiments
    experimentsImportDirectory = econfig.experimentsImportDirectory
    utils.checkDirectory(experimentsImportDirectory)
    experimentsDirectory = econfig.experimentsDir
    if projects is None:
        projects = utils.listDirectoryFolders(experimentsDirectory)
    Parallel(n_jobs=n_jobs)(delayed(experimentImport)(experimentsImportDirectory, experimentsDirectory, project) for project in projects)

def experimentImport(importDirectory, experimentsDirectory, project):
    """
    Generates all the entities and relationships
    from the specified Project. Called from function experimentsImport.
    Args:
        importDirectory (string): path to the directory where all the import
                        files are generated
        experimentDirectory (string): path to the directory where all the
                        experiments are located
        project (string): Identifier of the project to be imported
    """
    projectPath = os.path.join(importDirectory, project)
    utils.checkDirectory(projectPath)
    projectDirectory = os.path.join(experimentsDirectory, project)
    datasets = utils.listDirectoryFolders(projectDirectory)
    for dataset in datasets:
        datasetPath = os.path.join(projectPath, dataset)
        utils.checkDirectory(datasetPath)
        eh.generateDatasetImports(project, dataset)

def fullImport():
    """
    Calls the different importer functions: Ontologies, databases,
    experiments. The first step is to check if the stats object exists
    and create it otherwise. Calls setupStats.
    """
    importDirectory = config.importDirectory
    utils.checkDirectory(importDirectory)
    setupStats()
    ontologiesImport(importDirectory)
    print(datetime.now() - START_TIME)
    databasesImport(importDirectory, n_jobs=4)
    print(datetime.now() - START_TIME)
    experimentsImport(importDirectory, n_jobs=4)
    print(datetime.now() - START_TIME)

def generateStatsDataFrame(stats):
    """
    Generates a dataframe with the stats from each import.
    Args:
        stats (list): A list with statistics collected from each importer
                        function
    Returns:
        statsDf: pandas dataframe with the collected statistics
    """
    statsDf = pd.DataFrame.from_records(list(stats), columns=config.statsCols)
    return statsDf

def setupStats():
    """
    Creates a stats object that will collect all the statistics collected from
    each import.
    """
    statsDirectory = config.statsDirectory
    statsFile = os.path.join(statsDirectory, config.statsFile)
    statsCols = config.statsCols
    statsName = getStatsName()
    if not os.path.exists(statsDirectory) or not os.path.isfile(statsFile):
        if not os.path.exists(statsDirectory):
            os.makedirs(statsDirectory)
        createEmptyStats(statsCols, statsFile, statsName)

def createEmptyStats(statsCols, statsFile, statsName):
    """
    Creates a HDFStore object with a empty dataframe with the collected stats columns.
    Args:
        statsCols (list): A list of columns with the fields collected from the
                            import statistics
        statsFile (string): path where the object should be stored
        statsName (string): name if the file containing the stats object
    """
    statsDf = pd.DataFrame(columns=statsCols)
    hdf = pd.HDFStore(statsFile)
    hdf.put(statsName, statsDf, format='table', data_columns=True, min_itemsize=2000)
    hdf.close()

def loadStats(statsFile):
    """
    Loads the statistics object.
    Args:
        statsFile (string): File path where the stats object is stored.
    Returns:
        hdf (HDFStore object): object with the collected statistics.
                                stats can be accessed using a key
                                (i.e stats_ version)
    """
    hdf = None
    if os.path.isfile(statsFile):
        hdf = pd.HDFStore(statsFile)
    return hdf
def writeStats(statsDf, statsName=None):
    """
    Appends the new collected statistics to the existing stats object.
    Args:
        statsDf (dataframe): A pandas dataframe with the new statistics
                            from the importing.
        statsName (string): If the statistics should be stored with a
                            specific name
    """
    statsDirectory = config.statsDirectory
    statsFile = os.path.join(statsDirectory, config.statsFile)
    if statsName is None:
        statsName = getStatsName()
    hdf = loadStats(statsFile)
    hdf.append(statsName, statsDf, min_itemsize=2000)
    hdf.close()

def getStatsName():
    """
    Generates the stats object name where to store the importing
    statistics from the CKG version, which is defined in the configuration.
    Returns:
        statsName (string): key used to store in the stats object.
    """
    version = config.version
    statsName = 'stats_'+ str(version).replace('.', '_')

    return statsName


if __name__ == "__main__":
    fullImport()