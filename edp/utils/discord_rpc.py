"""
Discord app rpc client
"""
import enum
import json
import logging
import os
import struct
import uuid
from typing import BinaryIO, Optional, Tuple

from edp.utils import dict_subset

logger = logging.getLogger(__name__)


class RPC_OP(enum.Enum):
    """RCP OPs"""
    OP_HANDSHAKE = 0
    OP_FRAME = 1
    OP_CLOSE = 2
    OP_PING = 3
    OP_PONG = 4


class DiscordRpcClient:
    """Discord rpc server client"""

    def __init__(self, client_id: str):
        self._client_id = client_id
        self._pipe_file_handler: Optional[BinaryIO] = None

    # pylint: disable=no-self-use
    def _open_discord_rpc_pipe(self) -> Optional[BinaryIO]:
        for i in range(10):
            path = fr'\\?\pipe\discord-ipc-{i}'
            try:
                return open(path, "w+b")
            except OSError:
                logger.debug(f'Failed to connect to discord rpc server at "{path}"')
        return None

    @property
    def _pipe_file(self) -> BinaryIO:
        if not self._pipe_file_handler:
            file_handler = self._open_discord_rpc_pipe()
            if not file_handler:
                raise ConnectionError('Failed to connect to discord rpc server')
            self._pipe_file_handler = file_handler
            if not self._handshake():
                self._pipe_file_handler = None
                raise ConnectionError('Handshake failed')

        return self._pipe_file_handler

    def _send(self, data: dict, op: RPC_OP = RPC_OP.OP_FRAME):
        """
        Send data to discord rpc server

        :raises ConnectionError: if sending data fails
        """
        data_str = json.dumps(data, separators=(',', ':'))
        data_bytes = data_str.encode('utf-8')
        header = struct.pack("<II", op.value, len(data_bytes))
        try:
            self._pipe_file.write(header)
            self._pipe_file.write(data_bytes)
            self._pipe_file.flush()
        except ConnectionError:
            raise
        except:
            logger.exception('Error sending request to discord rpc server')
            self._pipe_file_handler = None
            raise ConnectionError('Failed to send data to discord rpc server')

    def _read_exactly(self, size: int) -> bytes:
        buf = b""
        size_remaining = size
        while size_remaining:
            try:
                chunk = self._pipe_file.read(size_remaining)
            except:
                self._pipe_file_handler = None
                raise ConnectionError('Failed to read discord rpc server response')
            buf += chunk
            size_remaining -= len(chunk)
        return buf

    def _receive(self) -> Tuple[RPC_OP, dict]:
        header = self._read_exactly(8)
        op, length = struct.unpack("<II", header)
        data_bytes = self._read_exactly(length)
        data = json.loads(data_bytes.decode('utf-8'))
        return op, data

    def _handshake(self) -> bool:
        """Do a handshake routine. Return True if successful"""
        ret_op, ret_data = self.request({'v': 1, 'client_id': self._client_id}, op=RPC_OP.OP_HANDSHAKE)

        if RPC_OP(ret_op) is RPC_OP.OP_FRAME and \
                dict_subset(ret_data, 'cmd', 'evt') == {'cmd': 'DISPATCH', 'evt': 'READY'}:
            return True

        if RPC_OP(ret_op) is RPC_OP.OP_CLOSE:
            self.close()
            return False

        return False

    def request(self, data: dict, op: RPC_OP = RPC_OP.OP_FRAME) -> Tuple[RPC_OP, dict]:
        """Send data to rpc server and return its response"""
        self._send(data, op)
        return self._receive()

    def close(self):
        """Close connection"""
        if self._pipe_file_handler:
            try:
                self._send({}, op=RPC_OP.OP_CLOSE)
            finally:
                if self._pipe_file_handler:
                    self._pipe_file_handler.close()
                    self._pipe_file_handler = None

    def set_activity(self, activity: dict):
        """Set discord rich presence activity"""
        data = {
            'cmd': 'SET_ACTIVITY',
            'args': {
                'pid': os.getpid(),
                'activity': activity
            },
            'nonce': str(uuid.uuid4())
        }
        return self.request(data)[1]
