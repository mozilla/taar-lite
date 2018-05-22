import redis
import boto3
import json
from srgutil.interfaces import IMozLogging


class LazyJSONLoader:
    def __init__(self, ctx, s3_bucket, s3_key, expiry=14400):
        self._ctx = ctx

        if not self.ignore_redis():
            self._redis = redis.StrictRedis(host='localhost', port=6379, db=0)

        self.logger = self._ctx[IMozLogging].get_logger('srgutil')

        self._s3_bucket = s3_bucket
        self._s3_key = s3_key

        self._expiry_seconds = expiry
        self._cached_copy = None

    def ignore_redis(self):
        return self._ctx.get('ignore_redis', False)

    def force_expiry(self):
        if self.ignore_redis():
            return

        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # Clear the byte cache in redis as well as locally cached copy
        self._redis.delete(key_str)
        self._cached_copy = None

    def get(self):
        """Fetch the value that is stored"""

        if self.ignore_redis():
            return self._get_json()

        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # If we have no cached copy, we explicitly want to clear the
        # byte cache in redis
        if self._cached_copy is None:
            self._redis.delete(key_str)
            self._cached_copy = self._get_json()
        else:
            # Reload data if the data is expired
            if not self._redis.exists(key_str):
                self._cached_copy = self._get_json()

        return self._cached_copy

    def _get_json(self):
        """Download and parse a json file stored on AWS S3.

        The file is downloaded and then cached for future use.
        """

        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        raw_data = None
        raw_bytes = None
        try:
            if not self.ignore_redis():
                raw_bytes = self._redis.get(key_str)

            if raw_bytes is None:
                lock_var = None
                if not self.ignore_redis():
                    lock_var = self._redis.lock("lock|{}".format(key_str), timeout=30)
                try:
                    if not self.ignore_redis():
                        lock_var.acquire(blocking=True)

                    raw_bytes = self._load_from_s3(key_str)

                    if not self.ignore_redis():
                        self._redis.set(key_str, raw_bytes, ex=self._expiry_seconds)
                finally:
                    if not self.ignore_redis():
                        lock_var.release()

            raw_data = (
                raw_bytes.decode('utf-8')
            )
        except Exception:
            self.logger.exception("Failed to download from S3", extra={
                "bucket": self._s3_bucket,
                "key": self._s3_key})
            return None

        # It can happen to have corrupted files. Account for the
        # sad reality of life.
        try:
            return json.loads(raw_data)
        except ValueError:
            self.logger.error("Cannot parse JSON resource from S3", extra={
                "bucket": self._s3_bucket,
                "key": self._s3_key})
        return None

    def _load_from_s3(self, key_str):
        s3 = boto3.resource('s3')
        raw_bytes = (
            s3
            .Object(self._s3_bucket, self._s3_key)
            .get()['Body']
            .read()
        )
        msg = "Loaded JSON from S3: {}".format(key_str)
        self.logger.info(msg)
        return raw_bytes
