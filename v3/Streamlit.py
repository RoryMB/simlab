import pickle
import time
from threading import Event, Thread

import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st
import zmq
from utils import DSH_ADDR, Flags, NodeFlags

st.set_page_config(layout="wide")

cm = {
    NodeFlags.Ready: 'green',
    NodeFlags.Running: 'orange',
    NodeFlags.Done: 'gray',
    NodeFlags.Failed: 'red',
}

def make_graph(graph):
    plt.close()
    fig, ax = plt.subplots(figsize=(8, 7))

    nx.draw(
        graph,
        ax=ax,
        pos=nx.nx_agraph.graphviz_layout(graph, prog='dot'),
        labels={n:n.name for n in graph.nodes},
        node_color=[cm.get(n._state) for n in graph.nodes],
        with_labels=True,
        font_size=7,
        arrowsize=5,
        node_size=90,
        # margins=(0.3, 0),
    )
    # nx.draw(
    #     graph,
    #     ax=ax,
    #     pos=nx.nx_agraph.graphviz_layout(graph, prog='dot'),
    #     with_labels=True,
    # )
    fig.patch.set_facecolor((0.75, 0.75, 0.75))

    return fig

def main():
    st.title('SimLab Dashboard')

    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.header('Graph')
            graph_container = st.empty()

        with col2:
            st.header('Jobs')
            job_container = st.empty()

        with col3:
            st.header('Resources')
            resource_container = st.empty()

    st.divider()

    context = zmq.Context()
    with context.socket(zmq.SUB) as sock:
        sock.connect(DSH_ADDR)
        sock.setsockopt(zmq.SUBSCRIBE, Flags.DASH_DETAILS)

        poller = zmq.Poller()
        poller.register(sock, zmq.POLLIN)

        while True:
            msg = sock.recv_multipart()

            # Check if we are way behind...
            socks = dict(poller.poll(timeout=0))
            if socks.get(sock) == zmq.POLLIN:
                # Skip if there's already a new message
                print('BEHIND! Skipping a message to keep up')
                continue

            try:
                match msg:
                    case [Flags.DASH_DETAILS, b]:
                        graph, jobs, resources, resource_locks = pickle.loads(b)
                    case _:
                        assert False
            except Exception:
                print('Problem with message')
                continue



            x = sorted([job._id for job in jobs.values()])
            if 'rmbsimlab.job' not in st.session_state or st.session_state['rmbsimlab.job'] != x:
                st.session_state['rmbsimlab.job'] = x
                job_container.empty()
                time.sleep(0.01)

            x = sorted([res._id for res in resources])
            if 'rmbsimlab.res' not in st.session_state or st.session_state['rmbsimlab.res'] != x:
                st.session_state['rmbsimlab.res'] = x
                resource_container.empty()
                time.sleep(0.01)



            with job_container.container():
                for job in jobs.values():
                    st.subheader(f'Job ID {job._id}')
                    st.pyplot(make_graph(job.graph))
                    st.divider()

            with graph_container.container():
                st.pyplot(make_graph(graph))

            with resource_container.container():
                for resource in resources:
                    if 'variant' in resource.features:
                        st.subheader(f'Resource ({resource.features["variant"]})')
                    else:
                        st.subheader('Resource, type unknown')
                    st.write(resource.features)
                    st.divider()

if __name__ == '__main__':
    main()
