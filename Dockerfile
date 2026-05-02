FROM icr.io/appcafe/websphere-liberty:full-java8-openj9-ubi

USER root

RUN mkdir -p \
    /config/apps \
    /opt/ibm/wlp/usr/shared/resources/Daytrader3_SampleDerbyLibs

COPY --chown=1001:0 daytrader3-ee6-wlpcfg/servers/daytrader3_Sample/server.xml /config/server.xml
COPY --chown=1001:0 daytrader3-ee6-wlpcfg/servers/daytrader3_Sample/apps/daytrader3-ee6.ear /config/apps/daytrader3-ee6.ear
COPY --chown=1001:0 daytrader3-ee6-wlpcfg/shared/resources/Daytrader3_SampleDerbyLibs/derby-10.10.1.1.jar /opt/ibm/wlp/usr/shared/resources/Daytrader3_SampleDerbyLibs/derby-10.10.1.1.jar

RUN configure.sh

USER 1001

EXPOSE 9083 9443
