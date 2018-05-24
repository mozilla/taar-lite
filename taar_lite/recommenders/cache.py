import redis
import boto3
import json
from srgutil.interfaces import IMozLogging


class LazyJSONLoader:
    def __init__(self, ctx, s3_bucket, s3_key, expiry=14400):
        self._ctx = ctx

        self._redis = redis.StrictRedis.from_url(ctx['CACHE_URL'])

        self.logger = self._ctx[IMozLogging].get_logger('srgutil')

        self._s3_bucket = s3_bucket
        self._s3_key = s3_key

        self._key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        self.logger = self._ctx[IMozLogging].get_logger('srgutil')

        self._expiry_seconds = expiry
        self.logger.info("Set expiry time to {}".format(self._expiry_seconds))

        self._cached_copy = None

    def force_expiry(self):
        key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        # Clear the byte cache in redis as well as locally cached copy
        self._redis.delete(key_str)
        self._cached_copy = None

    def get(self):
        """Fetch the value that is stored"""

        raw_data = None
        raw_bytes = None
        try:
            # We must acquire a lock to redis as we're checking across
            # the redis cache and the local _cached_copy of data.
            # The redis cache is a distributed lock so we don't need
            # to lock the process using python thread locks.
            #
            # Note that we need to hold the redis lock until we
            # return a value or have updated redis with new data
            # and a new expiration time.
            with self._redis.lock("lock|{}".format(self._key_str), timeout=60):
                # If the redis cache is hot and we have a cached copy
                # still, just return the cached copy
                if self._redis.exists(self._key_str) and self._cached_copy is not None:
                    return self._cached_copy

            # Loading cache data from redis doesn't need to be in a
            # lock.  The data will either be there or it won't.
            #
            # If the data is available in redis, we update the process
            # local copy of _cached_copy.
            #
            # If the data is not available in redis, we load from S3,
            # write the bytes to redis and then update the local copy
            # of _cached_copy.
            #
            # Neither case needs to be run in a lock as the worst case
            # scenario is that multiple threads will concurrently
            # write the same data to redis and the same data will
            # be decoded on each execution thread and stored in
            # _cached_copy.
            raw_bytes = self._redis.get(self._key_str)

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
                msg = "Loaded JSON from S3: {}".format(self._key_str)
                self.logger.info(msg)
                self._redis.set(self._key_str, raw_bytes, ex=self._expiry_seconds)
            else:
                # redis has a cached copy of the dataset.  Just
                # continue on to decode the data
                pass

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
