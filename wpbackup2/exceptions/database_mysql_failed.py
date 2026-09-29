""" wpbackup2 database exception: WpDatabaseMysqlFailedError """

class WpDatabaseMysqlFailed(Exception):
    """
    Raised when the mysql command fails

    Args:
        message (str): message
        stdOut (str): standard output.
        stdErr (str): standard error.
    """

    def __init__(self, message, stdOut, stdError):
        tmp = ('"{}.\nStdOut: "{}"\nStdErr: "{}"')
        msg = tmp.format(message, stdOut, stdError)
        super().__init__(msg)
