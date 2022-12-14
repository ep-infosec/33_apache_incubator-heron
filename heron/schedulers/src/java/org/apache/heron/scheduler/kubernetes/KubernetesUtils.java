/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.apache.heron.scheduler.kubernetes;

import java.io.IOException;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.apache.heron.common.basics.ByteAmount;
import org.apache.heron.common.basics.SysUtils;
import org.apache.heron.scheduler.TopologySubmissionException;
import org.apache.heron.scheduler.utils.Runtime;
import org.apache.heron.spi.common.Config;
import org.apache.heron.spi.common.Context;

import io.kubernetes.client.openapi.ApiException;
import okhttp3.Response;

final class KubernetesUtils {

  private static final String CONTAINER = "kubernetes";

  private KubernetesUtils() {
  }

  static String getConfCommand(Config config) {
    return String.format("%s %s", Context.downloaderConf(config), CONTAINER);
  }

  static String getFetchCommand(Config config, Config runtime) {
    return String.format("%s %s .", Context.downloaderBinary(config),
        Runtime.topologyPackageUri(runtime).toString());
  }

  static void logResponseBodyIfPresent(Logger log, Response response) {
    try {
      log.log(Level.SEVERE, "Error details:\n" +  response.body().string());
    } catch (IOException ioe) {
      // ignore
      SysUtils.closeIgnoringExceptions(response.body());
    }
  }

  static void logExceptionWithDetails(Logger log, String message, Exception e) {
    log.log(Level.SEVERE, message + " " + e.getMessage());
    if (e instanceof ApiException) {
      log.log(Level.SEVERE, "Error details:\n" +  ((ApiException) e).getResponseBody());
    }
  }

  static String errorMessageFromResponse(Response response) {
    final String message = response.message();
    String details;
    try {
      details = response.body().string();
    } catch (IOException ioe) {
      // ignore
      details = ioe.getMessage();
    } finally {
      SysUtils.closeIgnoringExceptions(response.body());
    }
    return message + "\ndetails:\n" + details;
  }

  // https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/
  // #meaning-of-memory
  static String Megabytes(ByteAmount amount) {
    return String.format("%sMi", Long.toString(amount.asMegabytes()));
  }

  static double roundDecimal(double value, int places) {
    double scale = Math.pow(10, places);
    return Math.round(value * scale) / scale;
  }

  static class CommonUtils<T> {
    private static final Logger LOG = Logger.getLogger(KubernetesShim.class.getName());

    /**
     * Merge two lists by keeping all values in the <code>primaryList</code> and de-duplicating values in
     * <code>secondaryList</code> using the <code>comparator</code>.
     * @param primaryList All the values in this will be retained.
     * @param secondaryList The values in this list will be deduplicated against <code>primaryList</code>.
     * @param comparator Used to compare keys in the <code>TreeSet</code> to find their insertion position.
     * @param description Description of the list merge operation which is used for error messages.
     * @return A de-duplicated list of all the values in both input lists using the <code>comparator</code>.
     */
    protected List<T> mergeListsDedupe(List<T> primaryList, List<T> secondaryList,
                                       Comparator<T> comparator, String description) {
      if (primaryList == null || primaryList.isEmpty()) {
        return secondaryList;
      }
      if (secondaryList == null || secondaryList.isEmpty()) {
        return primaryList;
      }
      try {
        Set<T> treeSet = new TreeSet<>(comparator);
        treeSet.addAll(primaryList);
        treeSet.addAll(secondaryList);
        return new LinkedList<>(treeSet);
      } catch (NullPointerException e) {
        final String message = String.format("Failed to merge lists for %s", description);
        LOG.log(Level.FINE, message);
        throw new TopologySubmissionException(message);
      }
    }
  }

  /**
   * Generic testing class for test runners in Kubernetes Scheduler.
   * @param <T1> Test input object type.
   * @param <T2> Expected test object type.
   */
  static class TestTuple<T1, T2> {
    public final String description;
    public final T1 input;
    public final T2 expected;

    /**
     * Configure the test object.
     * @param description Description of the test to be run.
     * @param input Input test case.
     * @param expected Expected output form test.
     */
    TestTuple(String description, T1 input, T2 expected) {
      this.description = description;
      this.expected = expected;
      this.input = input;
    }
  }
}
