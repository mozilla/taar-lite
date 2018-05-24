import redis
import boto3
import json
from srgutil.interfaces import IMozLogging
from threading import RLock


class LazyJSONLoader:
    def __init__(self, ctx, s3_bucket, s3_key, expiry=14400):
        self._ctx = ctx

        self._redis = redis.StrictRedis.from_url(ctx['CACHE_URL'])

        self.logger = self._ctx[IMozLogging].get_logger('srgutil')

        self._s3_bucket = s3_bucket
        self._s3_key = s3_key

        self._expiry_seconds = expiry
        self._cached_copy = None
        self._thread_lock = RLock()

    def force_expiry(self):
        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # Clear the byte cache in redis as well as locally cached copy
        self._redis.delete(key_str)
        self._cached_copy = None

    def get(self):
        """Fetch the value that is stored"""

        # We need to acquire a lock as multiple threads
        # may try to access the same loader instance when
        # running under gunicorn
        with self._thread_lock:
            key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

            # If we have no cached copy, we explicitly want to clear the
            # byte cache in redis
            if self._cached_copy is None:
                self._redis.delete(key_str)

            raw_data = None
            raw_bytes = None
            try:
                # We must acquire a lock to redis as we're checking across
                # the redis cache and the local _cached_copy of data.
                # Python will protect us from multithreaded access to
                # self._cached_copy but we need a redis lock to
                # provide safety across gunicorn processes.
                #
                # Note that we need to hold the redis lock until we
                # return a value or have updated redis with new data
                # and a new expiration time.
                with self._redis.lock("lock|{}".format(key_str), timeout=60):
                    # If the redis cache is hot and we have a cached copy
                    # still, just return the cached copy
                    if self._redis.exists(key_str) and self._cached_copy is not None:
                        return self._cached_copy

                    # Loading data is atomic, don't need a lock
                    raw_bytes = self._redis.get(key_str)

                    if raw_bytes is None:
                        # The raw_bytes data has expired from the redis cache.
                        # We need to force a data reload from S3
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

                # It is possible to have corrupted files in S3, so
                # protect against that.
                try:
                    self._cached_copy = json.loads(raw_data)
                except ValueError:
                    # Explicitly set the local cached_copy to None
                    self._cached_copy = None

                    self.logger.error("Cannot parse JSON resource from S3", extra={
                        "bucket": self._s3_bucket,
                        "key": self._s3_key})

                return self._cached_copy
            except Exception:
                self.logger.exception("Failed to download from S3", extra={
                    "bucket": self._s3_bucket,
                    "key": self._s3_key})
                return None
