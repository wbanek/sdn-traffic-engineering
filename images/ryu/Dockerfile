FROM python:3.9-slim
RUN pip install --no-cache-dir setuptools==58.2.0 wheel && \
    pip install --no-cache-dir --no-build-isolation eventlet==0.30.2 dnspython==1.16.0 ryu==4.34
WORKDIR /controllers
EXPOSE 6653
CMD ["ryu-manager", "--ofp-tcp-listen-port", "6653", "ryu.app.simple_switch_13"]