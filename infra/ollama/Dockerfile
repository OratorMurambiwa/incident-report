FROM python:3.12-slim AS fetch
COPY fetch_runtime.py fetch_source.py /
RUN python /fetch_runtime.py && python /fetch_source.py
FROM debian:bookworm-slim AS cpu
RUN apt-get update && apt-get install -y --no-install-recommends cmake g++ make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY --from=fetch /out/source.tar.gz /source.tar.gz
RUN tar xzf /source.tar.gz --strip-components=1 \
    && sed -i 's/set(GGML_CPU_ALL_VARIANTS ON)/set(GGML_CPU_ALL_VARIANTS OFF)/' CMakeLists.txt \
    && cmake -B build -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DCMAKE_INSTALL_PREFIX=/out \
    && cmake --build build --target ggml-cpu --parallel 2 \
    && cmake --install build --component CPU --strip
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=fetch /out/ollama /usr/local/bin/ollama
COPY --from=cpu /out/lib/ollama /usr/local/lib/ollama
ENV OLLAMA_HOST=0.0.0.0:11434 HOME=/root
EXPOSE 11434
ENTRYPOINT ["/usr/local/bin/ollama"]
CMD ["serve"]
