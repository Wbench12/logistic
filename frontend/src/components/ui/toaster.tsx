"use client";

import {
  Toaster as ChakraToaster,
  Portal,
  Spinner,
  Stack,
  Toast,
  createToaster,
} from "@chakra-ui/react";

export const toaster = createToaster({
  placement: "top-end",
  pauseOnPageIdle: true,
});

export const Toaster = () => {
  return (
    <Portal>
      <ChakraToaster toaster={toaster} insetInline={{ mdDown: "4" }}>
        {(toast) => (
          <Toast.Root 
            width={{ md: "sm" }} 
            // Force a background and text color based on type
            bg={
                toast.type === "error" ? "red.600" :
                toast.type === "success" ? "green.600" :
                toast.type === "info" ? "blue.600" :
                "gray.700"
            }
            color="white"
            borderRadius="lg"
            p={4}
            boxShadow="lg"
          >
            {toast.type === "loading" ? (
              <Spinner size="sm" color="white" />
            ) : (
              <Toast.Indicator color="white" />
            )}
            <Stack gap="1" flex="1" maxWidth="100%">
              {toast.title && (
                <Toast.Title fontWeight="bold" color="white">{toast.title}</Toast.Title>
              )}
              {toast.description && (
                <Toast.Description color="whiteAlpha.900">
                  {toast.description}
                </Toast.Description>
              )}
            </Stack>
            {toast.action && (
              <Toast.ActionTrigger>{toast.action.label}</Toast.ActionTrigger>
            )}
            <Toast.CloseTrigger color="whiteAlpha.800" _hover={{ color: "white" }} />
          </Toast.Root>
        )}
      </ChakraToaster>
    </Portal>
  );
};