FROM python:3.7 AS builder

COPY . /src
RUN pip wheel --wheel-dir=/root/wheels -r /src/requirements.txt

FROM python:3.7-slim

COPY . /src

# Setup git for ssh clones
RUN apt-get update -qq \
    && apt-get install -qq --no-install-recommends git openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir ~/.ssh \
    && chmod 0600 ~/.ssh \
    && ssh-keyscan github.com > ~/.ssh/known_hosts

COPY --from=builder /root/wheels /root/wheels
RUN pip install --disable-pip-version-check --no-cache-dir --find-links=/root/wheels --quiet /src \
    && rm -rf /root/wheels

# Setup env variable for tc-admin.py discovery
ENV TC_ADMIN_PY=/src/tc-admin.py

CMD "fuzzing-decision"
