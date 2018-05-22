import redis
import boto3
import json
from srgutil.interfaces import IMozLogging


class LazyJSONLoader:
    def __init__(self, ctx, s3_bucket, s3_key, expiry=14400):
        self._ctx = ctx

        self._redis = redis.StrictRedis(host='localhost', port=6379, db=0)

        self.logger = self._ctx[IMozLogging].get_logger('srgutil')

        self._s3_bucket = s3_bucket
        self._s3_key = s3_key

        self._expiry_seconds = expiry
        self._cached_copy = None

    def force_expiry(self):
        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # Clear the byte cache in redis as well as locally cached copy
        self._redis.delete(key_str)
        self._cached_copy = None

    def get(self):
        """Fetch the value that is stored"""
        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # If we have no cached copy, we explicitly want to clear the
        # byte cache in redis
        if self._cached_copy is None:
            self._redis.delete(key_str)

        return self._get_json()

    def _get_json(self):
        """Download and parse a json file stored on AWS S3.

        The file is downloaded and then cached for future use.
        """

        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        raw_data = None
        raw_bytes = None
        try:

            # If the redis cache is hot and we have a cached copy
            # still, just return the cached copy
            if self._redis.exists(key_str) and self._cached_copy is not None:
                return self._cached_copy

            raw_bytes = self._redis.get(key_str)

            if raw_bytes is None:
                with self._redis.lock("lock|{}".format(key_str), timeout=30):
                    s3 = boto3.resource('s3')
                    raw_bytes = (
                        s3
                        .Object(self._s3_bucket, self._s3_key)
                        .get()['Body']
                        .read()
                    )
                    msg = "Loaded JSON from S3: {}".format(key_str)
                    self.logger.info(msg)
                    self._redis.set(key_str, raw_bytes, ex=self._expiry_seconds)

            raw_data = (
                raw_bytes.decode('utf-8')
            )
        except Exception:
            self.logger.exception("Failed to download from S3", extra={
                "bucket": self._s3_bucket,
                "key": self._s3_key})
            return None

        # It can be possible to have corrupted files. Account for the
        # sad reality of life.
        try:
            self._cached_copy = json.loads(raw_data)
            return self._cached_copy
        except ValueError:
            self.logger.error("Cannot parse JSON resource from S3", extra={
                "bucket": self._s3_bucket,
                "key": self._s3_key})
        return None
